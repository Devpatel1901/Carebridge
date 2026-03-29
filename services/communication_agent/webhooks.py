"""Twilio webhook handlers — voice only (no SMS)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from starlette.requests import Request
from starlette.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from services.communication_agent.ai_interpreter import (
    interpret_appointment_choice,
    interpret_speech_response,
)
from services.communication_agent.elevenlabs_tts import tts_speak_url
from services.communication_agent.followup_db import patch_followup_job_status
from services.communication_agent.ngrok_compat import ngrok_free_skip_warning_params
from shared.cache import cache
from shared.config import get_settings
from shared.events.bus import event_bus
from shared.events.contracts import PatientResponseEvent, ResponseItem
from shared.logging import get_logger

logger = get_logger("webhooks")

MAX_CLARIFICATION_RETRIES = 2
VOICE_GATHER_TIMEOUT = 10
# Integer seconds — "auto" can cause TwiML/rendering issues on some Twilio accounts.
VOICE_SPEECH_TIMEOUT = "5"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_key_from_params(params: Any) -> str | None:
    """Resolve Redis key from URL (new: voice_session_id, legacy: patient_id)."""
    vsid = (params.get("voice_session_id") or "").strip()
    if vsid:
        return f"voice_session:{vsid}"
    pid = (params.get("patient_id") or "").strip()
    if pid:
        return f"voice_session:{pid}"
    return None


def _session_query_for_twiml(session: dict[str, Any], params: Any) -> dict[str, str]:
    """Query params that identify this call in every TwiML URL (Twilio needs absolute URLs)."""
    vsid = (session.get("voice_session_id") or "").strip()
    if vsid:
        return {"voice_session_id": vsid}
    pid = (session.get("patient_id") or "").strip()
    if pid:
        return {"patient_id": pid}
    vsid = (params.get("voice_session_id") or "").strip()
    if vsid:
        return {"voice_session_id": vsid}
    pid = (params.get("patient_id") or "").strip()
    if pid:
        return {"patient_id": pid}
    return {}


def _abs_voice_url(
    path: str,
    session: dict[str, Any],
    params: Any,
    extra: dict[str, str] | None = None,
) -> str:
    base = get_settings().twilio_webhook_base_url.strip().rstrip("/")
    q: dict[str, str] = {
        **ngrok_free_skip_warning_params(base),
        **_session_query_for_twiml(session, params),
    }
    if extra:
        q.update(extra)
    return f"{base}{path}?{urlencode(q)}"


def _twiml(vr: VoiceResponse) -> Response:
    return Response(
        content=str(vr),
        media_type="text/xml; charset=utf-8",
    )


def _build_gather(action: str, vr: VoiceResponse | None = None) -> Gather:
    return Gather(
        input="speech",
        action=action,
        method="POST",
        timeout=VOICE_GATHER_TIMEOUT,
        speech_timeout=VOICE_SPEECH_TIMEOUT,
        language="en-US",
    )


def _speak(element: VoiceResponse | Gather, text: str) -> None:
    """Speak text via ElevenLabs <Play> when configured, else fall back to Polly <Say>."""
    settings = get_settings()
    if settings.elevenlabs_api_key:
        element.play(tts_speak_url(text))
    else:
        element.say(text, voice="Polly.Joanna")


def _build_response_items(session: dict[str, Any]) -> list[ResponseItem]:
    items: list[ResponseItem] = []
    for r in session.get("responses", []):
        items.append(
            ResponseItem(
                question_id=r["question_id"],
                question_text=r["question_text"],
                answer=r["answer"],
                normalized=r.get("normalized"),
                clinical_flags=r.get("clinical_flags", []),
            )
        )
    return items


async def _publish_responses(session: dict[str, Any], call_sid: str | None = None) -> None:
    event = PatientResponseEvent(
        patient_id=session["patient_id"],
        interaction_id=str(uuid.uuid4()),
        questionnaire_id=session.get("questionnaire_id"),
        responses=_build_response_items(session),
        channel="voice",
        twilio_sid=call_sid,
    )
    await event_bus.publish(
        "patient_response_event",
        event,
        source_service="communication_agent",
    )
    logger.info(
        "responses_published",
        patient_id=session["patient_id"],
        response_count=len(session["responses"]),
        clinical_flags=[
            flag
            for r in session.get("responses", [])
            for flag in r.get("clinical_flags", [])
        ],
    )


# ---------------------------------------------------------------------------
# Voice: /webhooks/voice/start
# ---------------------------------------------------------------------------

async def voice_start_webhook(request: Request) -> Response:
    """Return initial TwiML for the outbound call — greeting + first question."""
    params = request.query_params
    session_key = _session_key_from_params(params)
    logger.info(
        "voice_start",
        session_key=session_key,
        voice_session_id=params.get("voice_session_id"),
    )

    vr = VoiceResponse()

    try:
        if not session_key:
            _speak(vr, "Sorry, this call link is invalid. Please contact your care team. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        session = await cache.get_json(session_key)

        if not session or not session.get("questions"):
            _speak(vr, "Sorry, we could not locate your follow-up questionnaire. Please contact your care team. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        patient_name = session.get("patient_name", "there")
        questions = session["questions"]
        first_q = questions[0]

        first_q_text = first_q.get("text") or "your first question"
        greeting_text = (
            f"Hello {patient_name}. "
            "This is CareBridge, calling for your post-discharge health check-in. "
            f"I have {len(questions)} question{'s' if len(questions) != 1 else ''} for you. "
            "Please speak your answer clearly after each question. "
            f"First question: {first_q_text}"
        )

        action_url = _abs_voice_url(
            "/webhooks/voice/gather",
            session,
            params,
            {"q_index": "0"},
        )
        gather = _build_gather(action_url)
        _speak(gather, greeting_text)
        vr.append(gather)

        _speak(vr, "I didn't hear a response. Let me repeat the question.")
        vr.redirect(
            _abs_voice_url("/webhooks/voice/start", session, params),
            method="GET",
        )

        return _twiml(vr)
    except Exception:
        logger.exception("voice_start.error")
        vr = VoiceResponse()
        _speak(vr, "We're having a technical issue. Please try again later. Goodbye.")
        vr.hangup()
        return _twiml(vr)


# ---------------------------------------------------------------------------
# Voice: /webhooks/voice/gather
# ---------------------------------------------------------------------------

async def voice_gather_webhook(request: Request) -> Response:
    """
    Process a patient's spoken answer via Claude, then advance to the next
    question or complete the call.
    """
    params = request.query_params
    session_key = _session_key_from_params(params)

    try:
        form = await request.form()
    except Exception:
        logger.exception("voice_gather.form_parse_error", session_key=session_key)
        vr = VoiceResponse()
        _speak(vr, "We're having a technical issue. Please try again later. Goodbye.")
        vr.hangup()
        return _twiml(vr)

    q_index = int(params.get("q_index", "0"))
    is_clarification = params.get("is_clarification", "false").lower() == "true"

    speech_result = str(form.get("SpeechResult", "")).strip()
    call_sid = str(form.get("CallSid", ""))

    logger.info(
        "voice_gather_received",
        session_key=session_key,
        q_index=q_index,
        is_clarification=is_clarification,
        speech=speech_result,
    )

    vr = VoiceResponse()

    try:
        if not session_key:
            _speak(vr, "Your session has expired. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        session = await cache.get_json(session_key)

        if not session:
            _speak(vr, "Your session has expired. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        patient_id = session.get("patient_id", "")

        questions = session["questions"]
        diagnosis = session.get("diagnosis", "Unknown")

        if q_index >= len(questions):
            await _finish_call(vr, session, call_sid, session_key)
            return _twiml(vr)

        current_q = questions[q_index]

        interpreted = await interpret_speech_response(
            question_text=current_q.get("text", ""),
            question_type=current_q.get("question_type", "open"),
            speech_result=speech_result,
            diagnosis=diagnosis,
        )

        if interpreted.needs_clarification:
            retry_key = f"retry_{q_index}"
            retries = session.get(retry_key, 0)

            if retries < MAX_CLARIFICATION_RETRIES:
                session[retry_key] = retries + 1
                await cache.set_json(session_key, session, expire_seconds=3600)

                clarification_text = (
                    interpreted.clarification_question
                    or "Could you please repeat or clarify your answer?"
                )
                logger.info(
                    "voice_gather.needs_clarification",
                    patient_id=patient_id,
                    q_index=q_index,
                    retry=retries + 1,
                )

                action_url = _abs_voice_url(
                    "/webhooks/voice/gather",
                    session,
                    params,
                    {"q_index": str(q_index), "is_clarification": "true"},
                )
                gather = _build_gather(action_url)
                _speak(gather, clarification_text)
                vr.append(gather)

                _speak(vr, "I didn't hear a response. Moving to the next question.")
                next_index = q_index + 1
                if next_index < len(questions):
                    vr.redirect(
                        _abs_voice_url(
                            "/webhooks/voice/gather",
                            session,
                            params,
                            {"q_index": str(next_index)},
                        ),
                        method="POST",
                    )
                else:
                    vr.redirect(
                        _abs_voice_url(
                            "/webhooks/voice/complete",
                            session,
                            params,
                            {"call_sid": call_sid},
                        ),
                        method="POST",
                    )
                return _twiml(vr)

            logger.warning(
                "voice_gather.max_retries_exceeded",
                patient_id=patient_id,
                q_index=q_index,
            )
            interpreted.needs_clarification = False
            interpreted.interpreted_answer = (
                interpreted.interpreted_answer
                or f"[Unclear response after {MAX_CLARIFICATION_RETRIES} attempts]"
            )

        session["responses"].append({
            "question_id": current_q.get("id", str(q_index)),
            "question_text": current_q.get("text", ""),
            "answer": interpreted.interpreted_answer,
            "normalized": interpreted.normalized,
            "clinical_flags": interpreted.clinical_flags,
            "raw_speech": interpreted.raw_speech,
        })
        session["current_index"] = q_index + 1
        session.pop(f"retry_{q_index}", None)

        # Inline appointment booking — intercept after the consent question is answered
        if current_q.get("id") == "q_appt_consent":
            consent_given = _inline_parse_consent(
                interpreted.interpreted_answer,
                interpreted.normalized,
            )
            logger.info(
                "voice_gather.consent_check",
                patient_id=session.get("patient_id"),
                raw_answer=interpreted.interpreted_answer,
                consent_given=consent_given,
            )
            if consent_given:
                await cache.set_json(session_key, session, expire_seconds=3600)
                await _transition_to_inline_booking(
                    vr, session, session_key, params, call_sid
                )
            else:
                _speak(vr, "No problem. Your care team has been notified. Take care, goodbye!")
                vr.hangup()
                await _publish_responses(session, call_sid=call_sid)
                await cache.delete(session_key)
            return _twiml(vr)

        next_index = q_index + 1

        if next_index < len(questions):
            next_q = questions[next_index]
            await cache.set_json(session_key, session, expire_seconds=3600)

            ack_phrases = {
                "yes": "Got it. ",
                "no": "Understood. ",
            }
            norm = (interpreted.normalized or "").lower()
            ack = ack_phrases.get(norm, "Thank you. ")
            next_q_text = next_q.get("text") or "the next question"
            next_text = f"{ack}Next question: {next_q_text}"

            action_url = _abs_voice_url(
                "/webhooks/voice/gather",
                session,
                params,
                {"q_index": str(next_index)},
            )
            gather = _build_gather(action_url)
            _speak(gather, next_text)
            vr.append(gather)

            _speak(vr, "I didn't hear a response. Let me repeat.")
            vr.redirect(
                _abs_voice_url(
                    "/webhooks/voice/gather",
                    session,
                    params,
                    {"q_index": str(next_index)},
                ),
                method="POST",
            )
        else:
            await _finish_call(vr, session, call_sid, session_key)

        return _twiml(vr)
    except Exception:
        logger.exception("voice_gather.error", session_key=session_key)
        vr = VoiceResponse()
        _speak(vr, "We're having a technical issue. Please try again later. Goodbye.")
        vr.hangup()
        return _twiml(vr)


# ---------------------------------------------------------------------------
# Voice: /webhooks/voice/complete  (gather fallback when moving past last Q)
# ---------------------------------------------------------------------------


async def voice_complete_webhook(request: Request) -> Response:
    """
    End the call when Twilio follows the gather fallback redirect (e.g. no
    speech on the last question during clarification). Must exist or Twilio
    gets 404 and reports an application error.
    """
    params = request.query_params
    call_sid_param = params.get("call_sid", "")

    call_sid = call_sid_param
    if request.method == "POST":
        form = await request.form()
        call_sid = str(form.get("CallSid", "") or call_sid_param)

    session_key = _session_key_from_params(params)
    logger.info("voice_complete", session_key=session_key, call_sid=call_sid)

    vr = VoiceResponse()

    try:
        if not session_key:
            _speak(vr, "Your session has ended. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        session = await cache.get_json(session_key)

        if not session:
            _speak(vr, "Your session has ended. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        await _finish_call(vr, session, call_sid, session_key)
        return _twiml(vr)
    except Exception:
        logger.exception("voice_complete.error", session_key=session_key)
        vr = VoiceResponse()
        _speak(vr, "We're having a technical issue. Please try again later. Goodbye.")
        vr.hangup()
        return _twiml(vr)


def _inline_parse_consent(answer: str, normalized: str = "") -> bool:
    """Return True if the patient's spoken consent answer is affirmative.

    Checks `normalized` ("yes"/"no") first — the most reliable signal — then
    falls back to token matching on the AI's interpreted_answer text.
    Negative patterns are checked before affirmatives so an explicit decline always wins.
    """
    # normalized == "yes" / "no" is the cleanest signal from the interpreter
    norm = (normalized or "").lower().strip()
    if norm == "no":
        return False
    if norm == "yes":
        return True

    if not answer:
        return False
    text = answer.lower().strip()

    negative_tokens = (
        "no ", "nope", "no,", "no.", "not ", "don't", "do not",
        "declines", "decline", "doesn't want", "does not want",
        "not interested", "no thank", "not at this",
    )
    if any(token in text for token in negative_tokens):
        return False

    raw_affirmatives = (
        "yes", "yeah", "yep", "yup", "sure", "please", "definitely",
        "absolutely", "of course", "i would", "i'd like", "i want",
        "would like", "sounds good", "that would", "go ahead",
    )
    if any(token in text for token in raw_affirmatives):
        return True

    # Broad paraphrase tokens — covers the many ways Claude summarises consent
    paraphrase_affirmatives = (
        "requests to schedule", "wants to schedule", "would like to schedule",
        "clearly requests", "requests an appointment", "wants an appointment",
        "would like an appointment", "asking to schedule", "expressed desire",
        "wishes to schedule", "has requested", "indicated they want",
        "patient requests", "patient wants",
        # Claude variants observed in production
        "consents to", "agrees to", "accepted", "confirmed appointment",
        "would like to book", "wants to book", "like to schedule",
        "has consented", "given consent", "expresses desire",
        "willing to", "open to scheduling",
    )
    return any(token in text for token in paraphrase_affirmatives)


async def _transition_to_inline_booking(
    vr: VoiceResponse,
    session: dict[str, Any],
    voice_session_key: str,
    params: Any,
    call_sid: str,
) -> None:
    """Seamlessly move from follow-up call into slot selection within the same call.

    1. Publishes clinical responses to the Brain Agent.
    2. Fetches available doctor slots.
    3. Creates a pending appointment record.
    4. Stores a new appt_session in Redis for the appointment/gather webhook.
    5. Appends slot-selection TwiML to vr (no second call placed).
    """
    patient_id = session.get("patient_id", "")
    patient_name = session.get("patient_name", "there")
    settings = get_settings()

    # Publish clinical responses to Brain Agent first (alerts/escalation can run in parallel)
    try:
        await _publish_responses(session, call_sid=call_sid)
    except Exception:
        logger.exception("inline_booking.publish_failed", patient_id=patient_id)

    # Clean up the original voice session — it has served its purpose
    try:
        await cache.delete(voice_session_key)
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Fetch available doctor slots
            slots_resp = await client.get(
                f"{settings.db_agent_url}/doctors/availability",
                params={"urgency": "medium", "limit": 3},
            )
            slots = slots_resp.json() if slots_resp.status_code == 200 else []

            if not slots:
                _speak(vr, "I'd like to schedule an appointment for you, but unfortunately there are no available slots right now. Your care team will call you to arrange a time. Take care, goodbye!")
                vr.hangup()
                logger.warning("inline_booking.no_slots", patient_id=patient_id)
                return

            # Create a pending appointment record
            appt_resp = await client.post(
                f"{settings.db_agent_url}/appointments",
                json={
                    "patient_id": patient_id,
                    "appointment_type": "followup",
                    "status": "pending_confirmation",
                    "notes": "Patient requested appointment during follow-up call.",
                },
            )
            appointment_id = (
                appt_resp.json().get("id", "")
                if appt_resp.status_code in (200, 201)
                else ""
            )
    except Exception:
        logger.exception("inline_booking.db_error", patient_id=patient_id)
        _speak(vr, "I'd like to schedule an appointment, but we're having a technical issue. Your care team will call you to arrange a time. Goodbye!")
        vr.hangup()
        return

    # Store a new appt_session keyed by a fresh UUID
    appt_session_id = str(uuid.uuid4())
    appt_session_key = f"appt_session:{appt_session_id}"
    appt_session = {
        "voice_session_id": appt_session_id,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "appointment_id": appointment_id,
        "slots": slots,
        "urgency": "medium",
        "retry_count": 0,
    }
    await cache.set_json(appt_session_key, appt_session, expire_seconds=3600)

    # Build slot-selection TwiML inline — gather action → existing appointment/gather webhook
    base = settings.twilio_webhook_base_url.strip().rstrip("/")
    ngrok_q = ngrok_free_skip_warning_params(base)
    q = {**ngrok_q, "voice_session_id": appt_session_id}
    gather_url = f"{base}/webhooks/voice/appointment/gather?{urlencode(q)}"
    repeat_url = f"{base}/webhooks/voice/appointment/start?{urlencode(q)}"

    slot_text = " ".join(_format_slot_for_speech(s, i) for i, s in enumerate(slots))
    prompt = (
        "Great! Let me check available appointment slots for you. "
        f"I have {len(slots)} available time{'s' if len(slots) != 1 else ''} with your doctor. "
        f"{slot_text} "
        "Which option works best for you? You can say the option number, the day, "
        "or tell me a preferred time."
    )

    gather = _build_gather(gather_url)
    _speak(gather, prompt)
    vr.append(gather)

    _speak(vr, "I didn't hear a response. Let me repeat the options.")
    vr.redirect(repeat_url, method="GET")

    logger.info(
        "inline_booking.transitioned",
        patient_id=patient_id,
        appointment_id=appointment_id,
        slots_offered=len(slots),
        appt_session_id=appt_session_id,
    )


async def _finish_call(
    vr: VoiceResponse,
    session: dict[str, Any],
    call_sid: str,
    session_key: str,
) -> None:
    """Say goodbye, publish responses, and clean up."""
    _speak(vr, "Thank you for completing your follow-up check-in. Your care team has been notified. Please do not hesitate to call us if you have any concerns. Take care and goodbye!")
    vr.hangup()

    sid = call_sid.strip() or None
    try:
        await _publish_responses(session, call_sid=sid)
    except Exception:
        logger.exception(
            "voice_finish.publish_failed",
            patient_id=session.get("patient_id"),
        )

    cid = session.get("schedule_correlation_id")

    try:
        await cache.delete(session_key)
    except Exception:
        logger.exception(
            "voice_finish.cache_delete_failed",
            session_key=session_key,
        )

    logger.info(
        "voice_call_complete",
        patient_id=session.get("patient_id"),
        total_responses=len(session.get("responses", [])),
    )

    if cid:
        await patch_followup_job_status(
            str(cid),
            "completed",
            completed_at=datetime.now(timezone.utc),
        )


# ---------------------------------------------------------------------------
# Voice: /webhooks/voice/status
# ---------------------------------------------------------------------------

async def voice_status_webhook(request: Request) -> Response:
    """Handle Twilio call-status callbacks (no-answer, busy, failed, etc.)."""
    try:
        form = await request.form()
        call_sid = str(form.get("CallSid", ""))
        call_status = str(form.get("CallStatus", ""))
        to = str(form.get("To", ""))

        logger.info(
            "voice_status_callback",
            call_sid=call_sid,
            call_status=call_status,
            to=to,
        )

        # Clean up Redis session for failed/short terminal statuses (not "completed" — _finish_call owns that).
        if call_status in ("no-answer", "busy", "failed", "canceled"):
            for prefix in ("voice_session:", "appt_session:"):
                keys = await cache.keys(f"{prefix}*")
                for key in keys:
                    session = await cache.get_json(key)
                    if session and session.get("call_sid") == call_sid:
                        if prefix == "voice_session:":
                            cid = session.get("schedule_correlation_id")
                            if cid:
                                await patch_followup_job_status(
                                    str(cid),
                                    "failed",
                                    completed_at=datetime.now(timezone.utc),
                                )
                        await cache.delete(key)
                        logger.info(
                            "voice_session_cleaned",
                            key=key,
                            call_status=call_status,
                        )
                        break
    except Exception:
        logger.exception("voice_status_callback.error")

    # Twilio expects an empty 200 response for status callbacks
    return Response(content="", status_code=200)


# ---------------------------------------------------------------------------
# Appointment booking voice webhooks
# ---------------------------------------------------------------------------

def _appt_session_key(params: Any) -> str | None:
    vsid = (params.get("voice_session_id") or "").strip()
    return f"appt_session:{vsid}" if vsid else None


def _format_slot_for_speech(slot: dict[str, Any], index: int) -> str:
    """Convert ISO slot_start to a human-friendly spoken string (Eastern, Windows-safe)."""
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    try:
        dt = datetime.fromisoformat(slot["slot_start"])
        # SQLite returns naive datetimes that represent UTC. Attach tzinfo before converting
        # so Python doesn't assume system local time.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_et = dt.astimezone(ZoneInfo("America/New_York"))
        # %-d / %-I are Linux-only; use lstrip("0") for cross-platform zero-stripping
        day_str = dt_et.strftime("%A, %B %d").replace(" 0", " ")
        hour = dt_et.strftime("%I").lstrip("0") or "12"
        minute_part = f":{dt_et.strftime('%M')}" if dt_et.minute else ""
        ampm = dt_et.strftime("%p")
        return f"Option {index + 1}: {day_str} at {hour}{minute_part} {ampm} Eastern with {slot['doctor_name']}."
    except Exception:
        return f"Option {index + 1}: with {slot['doctor_name']}."


async def appointment_voice_start_webhook(request: Request) -> Response:
    """Initial TwiML for the appointment booking call — reads out available slots."""
    params = request.query_params
    session_key = _appt_session_key(params)
    vr = VoiceResponse()

    try:
        if not session_key:
            _speak(vr, "Sorry, this call link is invalid. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        session = await cache.get_json(session_key)
        if not session:
            _speak(vr, "Sorry, we could not locate your appointment session. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        patient_name = session.get("patient_name", "there")
        slots = session.get("slots", [])

        if not slots:
            _speak(vr, f"Hello {patient_name}. Unfortunately we have no available appointment slots at this time. Your care team will contact you to schedule. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        slot_text = " ".join(_format_slot_for_speech(s, i) for i, s in enumerate(slots))
        greeting = (
            f"Hello {patient_name}. "
            "This is CareBridge. Based on your recent health check-in, your care team would like to schedule a follow-up appointment. "
            f"I have {len(slots)} available time{'s' if len(slots) != 1 else ''} for you. "
            f"{slot_text} "
            "Which option works best for you? You can say the option number, the day, or tell me a different preferred time."
        )

        base = get_settings().twilio_webhook_base_url.strip().rstrip("/")
        q = {**ngrok_free_skip_warning_params(base), "voice_session_id": session["voice_session_id"]}
        gather_url = f"{base}/webhooks/voice/appointment/gather?{urlencode(q)}"

        gather = _build_gather(gather_url)
        _speak(gather, greeting)
        vr.append(gather)

        _speak(vr, "I didn't hear a response. Let me repeat the options.")
        vr.redirect(
            f"{base}/webhooks/voice/appointment/start?{urlencode(q)}",
            method="GET",
        )
        return _twiml(vr)

    except Exception:
        logger.exception("appointment_voice_start.error")
        vr = VoiceResponse()
        _speak(vr, "We're having a technical issue. Please try again later. Goodbye.")
        vr.hangup()
        return _twiml(vr)


async def appointment_voice_gather_webhook(request: Request) -> Response:
    """Process patient's spoken slot choice via Claude, then confirm or retry."""
    params = request.query_params
    session_key = _appt_session_key(params)
    vr = VoiceResponse()

    try:
        form = await request.form()
    except Exception:
        logger.exception("appointment_voice_gather.form_error")
        _speak(vr, "We're having a technical issue. Please try again later. Goodbye.")
        vr.hangup()
        return _twiml(vr)

    speech_result = str(form.get("SpeechResult", "")).strip()
    call_sid = str(form.get("CallSid", ""))

    try:
        if not session_key:
            _speak(vr, "Your session has expired. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        session = await cache.get_json(session_key)
        if not session:
            _speak(vr, "Your session has expired. Goodbye.")
            vr.hangup()
            return _twiml(vr)

        slots = session.get("slots", [])
        patient_id = session.get("patient_id", "")
        appointment_id = session.get("appointment_id", "")
        retry_count = session.get("retry_count", 0)

        logger.info(
            "appointment_voice_gather.received",
            patient_id=patient_id,
            speech=speech_result,
            retry_count=retry_count,
        )

        choice = await interpret_appointment_choice(speech_result, slots)

        # --- Patient chose a valid slot ---
        if choice.chosen_slot_index is not None and 0 <= choice.chosen_slot_index < len(slots):
            chosen_slot = slots[choice.chosen_slot_index]
            settings = get_settings()

            async with httpx.AsyncClient(timeout=10.0) as client:
                confirm_resp = await client.post(
                    f"{settings.db_agent_url}/appointments/confirm",
                    json={
                        "slot_id": chosen_slot["id"],
                        "appointment_id": appointment_id,
                        "patient_id": patient_id,
                    },
                )

            if confirm_resp.status_code == 200:
                confirmed = confirm_resp.json()
                from datetime import datetime, timezone
                from zoneinfo import ZoneInfo
                try:
                    dt = datetime.fromisoformat(confirmed["scheduled_at"])
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    dt_et = dt.astimezone(ZoneInfo("America/New_York"))
                    day_str = dt_et.strftime("%A, %B %d").replace(" 0", " ")
                    hour = dt_et.strftime("%I").lstrip("0") or "12"
                    minute_part = f":{dt_et.strftime('%M')}" if dt_et.minute else ""
                    ampm = dt_et.strftime("%p")
                    spoken_time = f"{day_str} at {hour}{minute_part} {ampm} Eastern"
                except Exception:
                    spoken_time = confirmed.get("scheduled_at", "the scheduled time")
                doctor = confirmed.get("doctor_name", chosen_slot["doctor_name"])
                _speak(vr, f"Perfect. Your appointment has been confirmed for {spoken_time} with {doctor}. Your care team will send you a reminder. Take care and goodbye!")
                vr.hangup()
                await cache.delete(session_key)
                logger.info(
                    "appointment_confirmed",
                    patient_id=patient_id,
                    appointment_id=appointment_id,
                    scheduled_at=confirmed["scheduled_at"],
                )
                return _twiml(vr)

            elif confirm_resp.status_code == 409:
                # Race condition — slot was just taken
                logger.warning(
                    "appointment_voice_gather.slot_taken_race",
                    slot_id=chosen_slot["id"],
                    patient_id=patient_id,
                )
                # Offer next available slot if there is one (exclude the taken slot)
                remaining = [s for s in slots if s["id"] != chosen_slot["id"]]
                if remaining:
                    session["slots"] = remaining
                    await cache.set_json(session_key, session, expire_seconds=3600)
                    next_slot_text = " ".join(_format_slot_for_speech(s, i) for i, s in enumerate(remaining))
                    base = get_settings().twilio_webhook_base_url.strip().rstrip("/")
                    q = {**ngrok_free_skip_warning_params(base), "voice_session_id": session["voice_session_id"]}
                    gather_url = f"{base}/webhooks/voice/appointment/gather?{urlencode(q)}"
                    gather = _build_gather(gather_url)
                    _speak(gather, f"I'm sorry, that slot was just taken. Here are the remaining options: {next_slot_text} Which works for you?")
                    vr.append(gather)
                    return _twiml(vr)
                else:
                    settings_inner = get_settings()
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as c:
                            await c.patch(
                                f"{settings_inner.db_agent_url}/appointments/{appointment_id}",
                                json={
                                    "status": "pending_manual",
                                    "notes": "All available slots were taken during booking. Manual scheduling required.",
                                },
                            )
                    except Exception:
                        logger.exception("appointment_voice_gather.patch_failed_race", appointment_id=appointment_id)
                    _speak(vr, "I'm sorry, all available slots have just been taken. Your care team will call you to schedule. Goodbye.")
                    vr.hangup()
                    await cache.delete(session_key)
                    return _twiml(vr)
            else:
                logger.error("appointment_voice_gather.confirm_failed", status=confirm_resp.status_code)
                settings_err = get_settings()
                try:
                    async with httpx.AsyncClient(timeout=5.0) as c:
                        await c.patch(
                            f"{settings_err.db_agent_url}/appointments/{appointment_id}",
                            json={
                                "status": "pending_manual",
                                "notes": "Booking confirmation failed due to a system error. Manual scheduling required.",
                            },
                        )
                except Exception:
                    logger.exception("appointment_voice_gather.patch_failed_err", appointment_id=appointment_id)
                _speak(vr, "There was a problem confirming your appointment. Your care team will follow up. Goodbye.")
                vr.hangup()
                await cache.delete(session_key)
                return _twiml(vr)

        # --- Patient expressed a different preferred time ---
        if choice.preferred_time and retry_count < 1:
            settings = get_settings()
            session["retry_count"] = retry_count + 1
            async with httpx.AsyncClient(timeout=10.0) as client:
                slots_resp = await client.get(
                    f"{settings.db_agent_url}/doctors/availability",
                    params={"urgency": session.get("urgency", "medium"), "limit": 3},
                )
            new_slots = slots_resp.json() if slots_resp.status_code == 200 else slots
            session["slots"] = new_slots
            await cache.set_json(session_key, session, expire_seconds=3600)

            slot_text = " ".join(_format_slot_for_speech(s, i) for i, s in enumerate(new_slots))
            base = get_settings().twilio_webhook_base_url.strip().rstrip("/")
            q = {**ngrok_free_skip_warning_params(base), "voice_session_id": session["voice_session_id"]}
            gather_url = f"{base}/webhooks/voice/appointment/gather?{urlencode(q)}"
            gather = _build_gather(gather_url)
            _speak(gather, f"I understand you'd prefer {choice.preferred_time}. Here are our closest available times: {slot_text} Which option works best?")
            vr.append(gather)
            return _twiml(vr)

        # --- Needs clarification ---
        if choice.needs_clarification and retry_count < 1:
            session["retry_count"] = retry_count + 1
            await cache.set_json(session_key, session, expire_seconds=3600)
            clarification = choice.clarification_question or "Could you please repeat which option you'd prefer?"
            base = get_settings().twilio_webhook_base_url.strip().rstrip("/")
            q = {**ngrok_free_skip_warning_params(base), "voice_session_id": session["voice_session_id"]}
            gather_url = f"{base}/webhooks/voice/appointment/gather?{urlencode(q)}"
            gather = _build_gather(gather_url)
            _speak(gather, clarification)
            vr.append(gather)
            return _twiml(vr)

        # --- Fallback: max retries reached or no slot chosen ---
        # Persist the patient's expressed preference so nurses can act on it
        preferred = choice.preferred_time if choice else None
        note_parts = ["Manual scheduling required — automated booking unsuccessful."]
        if preferred:
            note_parts.append(f"Patient requested: {preferred}.")
        note_parts.append("Please call patient to confirm a suitable time.")
        fallback_note = " ".join(note_parts)

        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(
                    f"{settings.db_agent_url}/appointments/{appointment_id}",
                    json={"status": "pending_manual", "notes": fallback_note},
                )
        except Exception:
            logger.exception("appointment_voice_gather.patch_failed", appointment_id=appointment_id)

        _speak(vr, "We were unable to schedule your appointment automatically. Your care team will call you directly to find a suitable time. Goodbye.")
        vr.hangup()
        await cache.delete(session_key)
        logger.info(
            "appointment_booking.pending_manual",
            patient_id=patient_id,
            appointment_id=appointment_id,
            preferred_time=preferred,
        )
        return _twiml(vr)

    except Exception:
        logger.exception("appointment_voice_gather.error", session_key=session_key)
        vr = VoiceResponse()
        _speak(vr, "We're having a technical issue. Please try again later. Goodbye.")
        vr.hangup()
        return _twiml(vr)

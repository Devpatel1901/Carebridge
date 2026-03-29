"""Twilio webhook handlers — voice only (no SMS)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from services.communication_agent.ai_interpreter import interpret_speech_response
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
            vr.say(
                "Sorry, this call link is invalid. Please contact your care team. Goodbye.",
                voice="Polly.Joanna",
            )
            vr.hangup()
            return _twiml(vr)

        session = await cache.get_json(session_key)

        if not session or not session.get("questions"):
            vr.say(
                "Sorry, we could not locate your follow-up questionnaire. "
                "Please contact your care team. Goodbye.",
                voice="Polly.Joanna",
            )
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
        gather.say(greeting_text, voice="Polly.Joanna")
        vr.append(gather)

        vr.say(
            "I didn't hear a response. Let me repeat the question.",
            voice="Polly.Joanna",
        )
        vr.redirect(
            _abs_voice_url("/webhooks/voice/start", session, params),
            method="GET",
        )

        return _twiml(vr)
    except Exception:
        logger.exception("voice_start.error")
        vr = VoiceResponse()
        vr.say(
            "We're having a technical issue. Please try again later. Goodbye.",
            voice="Polly.Joanna",
        )
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
        vr.say(
            "We're having a technical issue. Please try again later. Goodbye.",
            voice="Polly.Joanna",
        )
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
            vr.say("Your session has expired. Goodbye.", voice="Polly.Joanna")
            vr.hangup()
            return _twiml(vr)

        session = await cache.get_json(session_key)

        if not session:
            vr.say("Your session has expired. Goodbye.", voice="Polly.Joanna")
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
                gather.say(clarification_text, voice="Polly.Joanna")
                vr.append(gather)

                vr.say(
                    "I didn't hear a response. Moving to the next question.",
                    voice="Polly.Joanna",
                )
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
            gather.say(next_text, voice="Polly.Joanna")
            vr.append(gather)

            vr.say("I didn't hear a response. Let me repeat.", voice="Polly.Joanna")
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
        vr.say(
            "We're having a technical issue. Please try again later. Goodbye.",
            voice="Polly.Joanna",
        )
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
            vr.say("Your session has ended. Goodbye.", voice="Polly.Joanna")
            vr.hangup()
            return _twiml(vr)

        session = await cache.get_json(session_key)

        if not session:
            vr.say("Your session has ended. Goodbye.", voice="Polly.Joanna")
            vr.hangup()
            return _twiml(vr)

        await _finish_call(vr, session, call_sid, session_key)
        return _twiml(vr)
    except Exception:
        logger.exception("voice_complete.error", session_key=session_key)
        vr = VoiceResponse()
        vr.say(
            "We're having a technical issue. Please try again later. Goodbye.",
            voice="Polly.Joanna",
        )
        vr.hangup()
        return _twiml(vr)


async def _finish_call(
    vr: VoiceResponse,
    session: dict[str, Any],
    call_sid: str,
    session_key: str,
) -> None:
    """Say goodbye, publish responses, and clean up."""
    vr.say(
        "Thank you for completing your follow-up check-in. "
        "Your care team has been notified. "
        "Please do not hesitate to call us if you have any concerns. "
        "Take care and goodbye!",
        voice="Polly.Joanna",
    )
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
            keys = await cache.keys("voice_session:*")
            for key in keys:
                session = await cache.get_json(key)
                if session and session.get("call_sid") == call_sid:
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

"""Twilio webhook handlers — voice only (no SMS)."""
from __future__ import annotations

import uuid
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from services.communication_agent.ai_interpreter import interpret_speech_response
from shared.cache import cache
from shared.events.bus import event_bus
from shared.events.contracts import PatientResponseEvent, ResponseItem
from shared.logging import get_logger

logger = get_logger("webhooks")

MAX_CLARIFICATION_RETRIES = 2
VOICE_GATHER_TIMEOUT = 8
VOICE_SPEECH_TIMEOUT = "auto"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _twiml(vr: VoiceResponse) -> Response:
    return Response(content=str(vr), media_type="text/xml")


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
    patient_id = request.query_params.get("patient_id", "")
    logger.info("voice_start", patient_id=patient_id)

    session_key = f"voice_session:{patient_id}"
    session = await cache.get_json(session_key)

    vr = VoiceResponse()

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

    greeting_text = (
        f"Hello {patient_name}. "
        "This is CareBridge, calling for your post-discharge health check-in. "
        f"I have {len(questions)} question{'s' if len(questions) != 1 else ''} for you. "
        "Please speak your answer clearly after each question. "
        f"First question: {first_q['text']}"
    )

    action_url = f"/webhooks/voice/gather?patient_id={patient_id}&q_index=0"
    gather = _build_gather(action_url)
    gather.say(greeting_text, voice="Polly.Joanna")
    vr.append(gather)

    # Fallback if no speech detected
    vr.say("I didn't hear a response. Let me repeat the question.", voice="Polly.Joanna")
    vr.redirect(f"/webhooks/voice/start?patient_id={patient_id}", method="GET")

    return _twiml(vr)


# ---------------------------------------------------------------------------
# Voice: /webhooks/voice/gather
# ---------------------------------------------------------------------------

async def voice_gather_webhook(request: Request) -> Response:
    """
    Process a patient's spoken answer via Claude, then advance to the next
    question or complete the call.
    """
    form = await request.form()
    params = request.query_params

    patient_id = params.get("patient_id", "")
    q_index = int(params.get("q_index", "0"))
    is_clarification = params.get("is_clarification", "false").lower() == "true"

    speech_result = str(form.get("SpeechResult", "")).strip()
    call_sid = str(form.get("CallSid", ""))

    logger.info(
        "voice_gather_received",
        patient_id=patient_id,
        q_index=q_index,
        is_clarification=is_clarification,
        speech=speech_result,
    )

    session_key = f"voice_session:{patient_id}"
    session = await cache.get_json(session_key)
    vr = VoiceResponse()

    if not session:
        vr.say("Your session has expired. Goodbye.", voice="Polly.Joanna")
        vr.hangup()
        return _twiml(vr)

    questions = session["questions"]
    diagnosis = session.get("diagnosis", "Unknown")

    # Current question being answered
    if q_index >= len(questions):
        # Safety: all questions already answered — wrap up
        await _finish_call(vr, session, call_sid, session_key)
        return _twiml(vr)

    current_q = questions[q_index]

    # --- Interpret the speech with Claude ---
    interpreted = await interpret_speech_response(
        question_text=current_q["text"],
        question_type=current_q.get("question_type", "open"),
        speech_result=speech_result,
        diagnosis=diagnosis,
    )

    if interpreted.needs_clarification:
        # Check retry count
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

            action_url = (
                f"/webhooks/voice/gather"
                f"?patient_id={patient_id}&q_index={q_index}&is_clarification=true"
            )
            gather = _build_gather(action_url)
            gather.say(clarification_text, voice="Polly.Joanna")
            vr.append(gather)

            # Fallback if still no speech
            vr.say("I didn't hear a response. Moving to the next question.", voice="Polly.Joanna")
            next_index = q_index + 1
            if next_index < len(questions):
                vr.redirect(
                    f"/webhooks/voice/gather?patient_id={patient_id}&q_index={next_index}",
                    method="POST",
                )
            else:
                vr.redirect(
                    f"/webhooks/voice/complete?patient_id={patient_id}&call_sid={call_sid}",
                    method="POST",
                )
            return _twiml(vr)

        else:
            # Max retries hit — store best-effort answer and move on
            logger.warning(
                "voice_gather.max_retries_exceeded",
                patient_id=patient_id,
                q_index=q_index,
            )
            interpreted.needs_clarification = False
            interpreted.interpreted_answer = (
                interpreted.interpreted_answer or f"[Unclear response after {MAX_CLARIFICATION_RETRIES} attempts]"
            )

    # --- Store the interpreted response ---
    session["responses"].append({
        "question_id": current_q["id"],
        "question_text": current_q["text"],
        "answer": interpreted.interpreted_answer,
        "normalized": interpreted.normalized,
        "clinical_flags": interpreted.clinical_flags,
        "raw_speech": interpreted.raw_speech,
    })
    session["current_index"] = q_index + 1
    # Clear retry counter for this question
    session.pop(f"retry_{q_index}", None)

    next_index = q_index + 1

    if next_index < len(questions):
        next_q = questions[next_index]
        await cache.set_json(session_key, session, expire_seconds=3600)

        # Acknowledge and ask next question
        ack_phrases = {
            "yes": "Got it. ",
            "no": "Understood. ",
        }
        ack = ack_phrases.get(interpreted.normalized.lower(), "Thank you. ")
        next_text = f"{ack}Next question: {next_q['text']}"

        action_url = f"/webhooks/voice/gather?patient_id={patient_id}&q_index={next_index}"
        gather = _build_gather(action_url)
        gather.say(next_text, voice="Polly.Joanna")
        vr.append(gather)

        # Fallback if no speech on next question
        vr.say("I didn't hear a response. Let me repeat.", voice="Polly.Joanna")
        vr.redirect(
            f"/webhooks/voice/gather?patient_id={patient_id}&q_index={next_index}",
            method="POST",
        )
    else:
        # All questions answered
        await _finish_call(vr, session, call_sid, session_key)

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

    await _publish_responses(session, call_sid=call_sid)
    await cache.delete(session_key)

    logger.info(
        "voice_call_complete",
        patient_id=session.get("patient_id"),
        total_responses=len(session.get("responses", [])),
    )


# ---------------------------------------------------------------------------
# Voice: /webhooks/voice/status
# ---------------------------------------------------------------------------

async def voice_status_webhook(request: Request) -> Response:
    """Handle Twilio call-status callbacks (no-answer, busy, failed, etc.)."""
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

    # Clean up Redis session for terminal statuses
    if call_status in ("no-answer", "busy", "failed", "canceled"):
        # Find session by scanning — the patient_id is stored inside session
        keys = await cache.keys("voice_session:*")
        for key in keys:
            session = await cache.get_json(key)
            if session and session.get("call_sid") == call_sid:
                await cache.delete(key)
                logger.info(
                    "voice_session_cleaned",
                    key=key,
                    call_status=call_status,
                )
                break

    # Twilio expects an empty 200 response for status callbacks
    return Response(content="", status_code=200)

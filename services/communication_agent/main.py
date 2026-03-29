from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
import time
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from twilio.twiml.voice_response import VoiceResponse

from services.communication_agent.config import SERVICE_NAME, SERVICE_PORT, comm_settings
from services.communication_agent.followup_db import patch_followup_job_status
from services.communication_agent.ngrok_compat import ngrok_free_skip_warning_params
from services.communication_agent.twilio_client import make_voice_call
from services.communication_agent.webhooks import (
    voice_complete_webhook,
    voice_gather_webhook,
    voice_start_webhook,
    voice_status_webhook,
)
from shared.cache import cache
from shared.events.bus import event_bus
from shared.logging import CorrelationIdMiddleware, get_logger, setup_logging
from shared.schemas.models import InitiateCallRequest

setup_logging()
logger = get_logger(SERVICE_NAME)


class TwilioVoiceRequestLogMiddleware(BaseHTTPMiddleware):
    """Log Twilio webhook requests — if these never appear, Twilio is not reaching this app."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/webhooks/voice"):
            return await call_next(request)
        t0 = time.perf_counter()
        logger.info(
            "twilio_http_in",
            method=request.method,
            path=path,
            query=str(request.query_params),
        )
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("twilio_http_error", path=path)
            raise
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.info(
            "twilio_http_out",
            path=path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = comm_settings.settings
    pub = s.twilio_webhook_base_url.strip().rstrip("/")
    logger.info(
        "starting",
        service=SERVICE_NAME,
        port=SERVICE_PORT,
        twilio_webhook_host=pub[:60] + ("…" if len(pub) > 60 else ""),
    )
    if "localhost" in pub or "127.0.0.1" in pub:
        logger.warning(
            "TWILIO_WEBHOOK_BASE_URL points to localhost — Twilio cannot reach it. "
            "Use your public HTTPS tunnel URL (e.g. ngrok) in .env and restart."
        )
    await event_bus.connect()
    await cache.connect()
    yield
    await cache.disconnect()
    await event_bus.disconnect()
    logger.info("stopped", service=SERVICE_NAME)


app = FastAPI(
    title="CareBridge Communication Agent",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(TwilioVoiceRequestLogMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# POST /initiate-call
# ---------------------------------------------------------------------------

@app.post("/initiate-call")
async def initiate_call(body: InitiateCallRequest) -> dict[str, Any]:
    """
    Initiate an outbound AI voice follow-up call for a patient.
    Fetches the patient record and disease-specific questionnaire, stores
    the session in Redis, then triggers the Twilio outbound call.
    """
    settings = comm_settings.settings
    patient_id = body.patient_id

    logger.info("initiate_call", patient_id=patient_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch patient from DB Agent
        patient_resp = await client.get(
            f"{settings.db_agent_url}/patients/{patient_id}"
        )
        if patient_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch patient from DB Agent: {patient_resp.text}",
            )
        patient = patient_resp.json()

        # Fetch disease-specific questionnaire from Brain Agent
        questions_resp = await client.get(
            f"{settings.brain_agent_url}/patients/{patient_id}/questions"
        )
        if questions_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch questions from Brain Agent: {questions_resp.text}",
            )
        questions_data = questions_resp.json()

    patient_phone = patient.get("phone", "")
    patient_name = patient.get("name", "")

    # Extract diagnosis from discharge summary for AI interpreter context
    discharge = patient.get("discharge_summary") or {}
    diagnosis = discharge.get("diagnosis", "Unknown")

    questions = questions_data.get(
        "questions",
        questions_data if isinstance(questions_data, list) else [],
    )
    questionnaire_id = questions_data.get("questionnaire_id")

    if not patient_phone:
        raise HTTPException(
            status_code=400,
            detail="Patient has no phone number on file.",
        )

    if not questions:
        raise HTTPException(
            status_code=400,
            detail="No questions generated for this patient yet. "
                   "Ensure the discharge intake has been processed.",
        )

    # One Redis session per outbound call (avoids overwrite/races when the same
    # patient is called again before the previous call finishes).
    voice_session_id = str(uuid.uuid4())
    session_key = f"voice_session:{voice_session_id}"
    session = {
        "voice_session_id": voice_session_id,
        "patient_id": patient_id,
        "patient_phone": patient_phone,
        "patient_name": patient_name,
        "diagnosis": diagnosis,
        "questionnaire_id": questionnaire_id,
        "schedule_correlation_id": body.schedule_correlation_id,
        "questions": [
            {
                "id": q.get("id", str(i)),
                "text": q["text"],
                "question_type": q.get("question_type", "open"),
            }
            for i, q in enumerate(questions)
        ],
        "current_index": 0,
        "responses": [],
        "channel": "voice",
    }

    await cache.set_json(session_key, session, expire_seconds=3600)

    # Build webhook URLs using the public ngrok base URL
    base = settings.twilio_webhook_base_url.strip().rstrip("/")
    ngrok_q = ngrok_free_skip_warning_params(base)
    start_q = urlencode({"voice_session_id": voice_session_id, **ngrok_q})
    start_url = f"{base}/webhooks/voice/start?{start_q}"
    status_url = (
        f"{base}/webhooks/voice/status?{urlencode(ngrok_q)}"
        if ngrok_q
        else f"{base}/webhooks/voice/status"
    )

    call_sid = await make_voice_call(
        to=patient_phone,
        twiml_url=start_url,
        status_callback_url=status_url,
    )

    # Persist call_sid in session so status webhook can find and clean it up
    session["call_sid"] = call_sid
    await cache.set_json(session_key, session, expire_seconds=3600)

    if body.schedule_correlation_id:
        await patch_followup_job_status(
            body.schedule_correlation_id,
            "in_progress",
            executed_at=datetime.now(timezone.utc),
        )

    logger.info(
        "call_initiated",
        patient_id=patient_id,
        call_sid=call_sid,
        phone=patient_phone,
    )

    return {
        "status": "initiated",
        "channel": "voice",
        "patient_id": patient_id,
        "voice_session_id": voice_session_id,
        "call_sid": call_sid,
    }


# ---------------------------------------------------------------------------
# Twilio webhook routes (voice only)
# ---------------------------------------------------------------------------

@app.get("/webhooks/voice/twiml-smoke")
async def twiml_smoke() -> Response:
    """
    Minimal TwiML (no Redis). Use to verify your tunnel returns XML the way Twilio sees it:

      curl -sS 'BASE/webhooks/voice/twiml-smoke' | head -1
    """
    vr = VoiceResponse()
    vr.say(
        "CareBridge webhook smoke test. If you hear this on a trial call, your tunnel works.",
        voice="Polly.Joanna",
    )
    vr.hangup()
    return Response(
        content=str(vr),
        media_type="text/xml; charset=utf-8",
    )


@app.get("/webhooks/voice/start")
async def handle_voice_start_get(request: Request):
    """GET variant — Twilio uses the URL passed to calls.create."""
    return await voice_start_webhook(request)


@app.post("/webhooks/voice/start")
async def handle_voice_start_post(request: Request):
    return await voice_start_webhook(request)


@app.post("/webhooks/voice/gather")
async def handle_voice_gather(request: Request):
    return await voice_gather_webhook(request)


@app.get("/webhooks/voice/complete")
@app.post("/webhooks/voice/complete")
async def handle_voice_complete(request: Request):
    """Gather fallback redirect — must match TwiML redirects from webhooks."""
    return await voice_complete_webhook(request)


@app.post("/webhooks/voice/status")
async def handle_voice_status(request: Request):
    return await voice_status_webhook(request)


# ---------------------------------------------------------------------------
# Active sessions
# ---------------------------------------------------------------------------

@app.get("/active-sessions")
async def active_sessions() -> list[dict[str, Any]]:
    keys = await cache.keys("voice_session:*")
    sessions: list[dict[str, Any]] = []
    for key in keys:
        session = await cache.get_json(key)
        if session:
            sessions.append({
                "session_key": key,
                "patient_id": session.get("patient_id"),
                "patient_name": session.get("patient_name"),
                "diagnosis": session.get("diagnosis"),
                "channel": "voice",
                "current_index": session.get("current_index"),
                "total_questions": len(session.get("questions", [])),
                "call_sid": session.get("call_sid"),
            })
    return sessions


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": SERVICE_NAME}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)

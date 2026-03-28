from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from services.communication_agent.config import SERVICE_NAME, SERVICE_PORT, comm_settings
from services.communication_agent.twilio_client import make_voice_call
from services.communication_agent.webhooks import (
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting", service=SERVICE_NAME, port=SERVICE_PORT)
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

    # Build Redis session — includes diagnosis for ai_interpreter context
    session_key = f"voice_session:{patient_id}"
    session = {
        "patient_id": patient_id,
        "patient_phone": patient_phone,
        "patient_name": patient_name,
        "diagnosis": diagnosis,
        "questionnaire_id": questionnaire_id,
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
    base = settings.twilio_webhook_base_url.rstrip("/")
    start_url = f"{base}/webhooks/voice/start?patient_id={patient_id}"
    status_url = f"{base}/webhooks/voice/status"

    call_sid = await make_voice_call(
        to=patient_phone,
        twiml_url=start_url,
        status_callback_url=status_url,
    )

    # Persist call_sid in session so status webhook can find and clean it up
    session["call_sid"] = call_sid
    await cache.set_json(session_key, session, expire_seconds=3600)

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
        "call_sid": call_sid,
    }


# ---------------------------------------------------------------------------
# Twilio webhook routes (voice only)
# ---------------------------------------------------------------------------

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

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from shared.events.bus import event_bus
from shared.events.contracts import (
    AlertEvent,
    AlertType,
    AppointmentBookingRequest,
    DecisionType,
    JobType,
    MedicationData,
    PatientResponseEvent,
    PatientStateUpsert,
    RiskLevel,
    ScheduleEvent,
    Severity,
)
from shared.logging import CorrelationIdMiddleware, get_logger, setup_logging
from shared.schemas.models import (
    DischargeIntakeRequest,
    DischargeIntakeResponse,
    EvaluateResponseRequest,
    EvaluateResponseResult,
)
from services.brain_agent.config import SERVICE_NAME
from services.brain_agent.graph import intake_chain, response_chain
from services.brain_agent.nodes import BrainState

setup_logging()
logger = get_logger(SERVICE_NAME)

# ---------------------------------------------------------------------------
# Event publishing helpers
# ---------------------------------------------------------------------------

async def _publish_actions(actions: list[dict[str, Any]]) -> None:
    """Walk the action list produced by action_generation_node and publish."""
    for action in actions:
        action_type = action.get("type")
        cid = action.get("correlation_id", "")

        if action_type == "patient_state_upsert":
            event = PatientStateUpsert(
                patient_id=action["patient_id"],
                correlation_id=cid,
                source_service=SERVICE_NAME,
                demographics={
                    "name": action["demographics"].get("name", "Unknown"),
                    "phone": action["demographics"].get("phone", ""),
                    "dob": action["demographics"].get("dob"),
                    "email": action["demographics"].get("email"),
                },
                discharge_data={
                    "diagnosis": action["discharge_data"].get("diagnosis", ""),
                    "procedures": action["discharge_data"].get("procedures"),
                    "discharge_date": action["discharge_data"].get("discharge_date"),
                    "instructions": action["discharge_data"].get("instructions"),
                    "raw_text": action["discharge_data"].get("raw_text", ""),
                },
                medications=[
                    MedicationData(**m) for m in action.get("medications", [])
                ],
                risk_level=RiskLevel(action.get("risk_level", "low")),
                generated_questions=action.get("generated_questions", []),
            )
            await event_bus.publish(
                "patient_state_upsert", event,
                correlation_id=cid, source_service=SERVICE_NAME,
            )

        elif action_type == "alert_event":
            event = AlertEvent(
                patient_id=action["patient_id"],
                correlation_id=cid,
                source_service=SERVICE_NAME,
                alert_type=AlertType(action.get("alert_type", "general")),
                severity=Severity(action.get("severity", "medium")),
                message=action.get("message", ""),
            )
            await event_bus.publish(
                "alert_event", event,
                correlation_id=cid, source_service=SERVICE_NAME,
            )

        elif action_type == "schedule_event":
            scheduled_at_raw = action.get("scheduled_at")
            scheduled_at = (
                datetime.fromisoformat(scheduled_at_raw)
                if scheduled_at_raw
                else None
            )
            event = ScheduleEvent(
                patient_id=action["patient_id"],
                correlation_id=cid,
                source_service=SERVICE_NAME,
                job_type=JobType(action.get("job_type", "followup")),
                scheduled_at=scheduled_at,
                metadata=action.get("metadata", {}),
            )
            await event_bus.publish(
                "schedule_event", event,
                correlation_id=cid, source_service=SERVICE_NAME,
            )

        elif action_type == "appointment_booking_request":
            event = AppointmentBookingRequest(
                patient_id=action["patient_id"],
                correlation_id=cid,
                source_service=SERVICE_NAME,
                urgency=action.get("urgency", "medium"),
                reason=action.get("reason", ""),
            )
            await event_bus.publish(
                "appointment_booking_request", event,
                correlation_id=cid, source_service=SERVICE_NAME,
            )

        else:
            logger.warning("unknown_action_type", action_type=action_type)


# ---------------------------------------------------------------------------
# Event consumer: patient_response_event
# ---------------------------------------------------------------------------

async def _handle_patient_response(envelope: dict[str, Any]) -> None:
    """Consume patient_response_event, run response_chain, publish actions."""
    payload = envelope.get("payload", {})
    cid = envelope.get("correlation_id", str(uuid.uuid4()))
    patient_id = payload.get("patient_id", "")

    logger.info(
        "handle_patient_response.start",
        patient_id=patient_id,
        correlation_id=cid,
    )

    settings = get_settings()
    diagnosis = "Unknown"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.db_agent_url}/patients/{patient_id}",
            )
            if resp.status_code == 200:
                patient_data = resp.json()
                ds = patient_data.get("discharge_summary") or {}
                diagnosis = ds.get("diagnosis", "Unknown")
    except Exception:
        logger.exception("handle_patient_response.fetch_patient_error")

    responses = payload.get("responses", [])

    initial_state: BrainState = {
        "patient_id": patient_id,
        "correlation_id": cid,
        "patient_response": {
            "responses": responses,
            "diagnosis": diagnosis,
        },
        "risk_evaluation": {"risk_level": "medium", "reasoning": "", "risk_factors": []},
    }

    result = await response_chain.ainvoke(initial_state)
    await _publish_actions(result.get("actions", []))

    logger.info(
        "handle_patient_response.done",
        patient_id=patient_id,
        decision=result.get("decision", {}).get("decision_type"),
    )


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("brain_agent.startup")
    await event_bus.connect()
    await event_bus.subscribe(
        "patient_response_event",
        _handle_patient_response,
        queue_name="brain_agent_patient_response_queue",
    )
    logger.info("brain_agent.ready")
    yield
    logger.info("brain_agent.shutdown")
    await event_bus.disconnect()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CareBridge Brain Agent",
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
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/intake", response_model=DischargeIntakeResponse)
async def intake(req: DischargeIntakeRequest):
    """Process a new discharge summary through the full intake pipeline."""
    existing = (req.existing_patient_id or "").strip()
    patient_id = existing if existing else str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())

    logger.info(
        "intake.start",
        patient_id=patient_id,
        patient_name=req.patient_name,
    )

    initial_state: BrainState = {
        "raw_text": req.discharge_summary_text,
        "patient_name": req.patient_name,
        "patient_phone": req.patient_phone,
        "patient_dob": req.patient_dob,
        "patient_email": req.patient_email,
        "patient_id": patient_id,
        "correlation_id": correlation_id,
    }

    result = await intake_chain.ainvoke(initial_state)

    await _publish_actions(result.get("actions", []))

    decision_raw = result.get("decision", {})
    risk_raw = result.get("risk_evaluation", {})
    questions = result.get("generated_questions", [])

    return DischargeIntakeResponse(
        patient_id=patient_id,
        risk_level=RiskLevel(risk_raw.get("risk_level", "medium")),
        decision=DecisionType(decision_raw.get("decision_type", "stable")),
        generated_questions=questions,
        correlation_id=correlation_id,
    )


@app.post("/evaluate-response", response_model=EvaluateResponseResult)
async def evaluate_response(req: EvaluateResponseRequest):
    """Evaluate patient follow-up responses through the response pipeline."""
    correlation_id = str(uuid.uuid4())

    logger.info(
        "evaluate_response.start",
        patient_id=req.patient_id,
    )

    settings = get_settings()
    diagnosis = "Unknown"
    risk_evaluation: dict[str, Any] = {
        "risk_level": "medium",
        "reasoning": "",
        "risk_factors": [],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.db_agent_url}/patients/{req.patient_id}",
            )
            if resp.status_code == 200:
                patient_data = resp.json()
                ds = patient_data.get("discharge_summary") or {}
                diagnosis = ds.get("diagnosis", "Unknown")
                if patient_data.get("risk_level"):
                    risk_evaluation["risk_level"] = patient_data["risk_level"]
    except Exception:
        logger.exception("evaluate_response.fetch_patient_error")

    responses_dicts = [r.model_dump() for r in req.responses]

    initial_state: BrainState = {
        "patient_id": req.patient_id,
        "correlation_id": correlation_id,
        "patient_response": {
            "responses": responses_dicts,
            "diagnosis": diagnosis,
        },
        "risk_evaluation": risk_evaluation,
    }

    result = await response_chain.ainvoke(initial_state)

    await _publish_actions(result.get("actions", []))

    decision_raw = result.get("decision", {})
    risk_raw = result.get("risk_evaluation", {})
    actions = result.get("actions", [])
    alerts = [a for a in actions if a.get("type") == "alert_event"]

    return EvaluateResponseResult(
        patient_id=req.patient_id,
        risk_level=RiskLevel(risk_raw.get("risk_level", "medium")),
        decision=DecisionType(decision_raw.get("decision_type", "stable")),
        alerts=alerts,
        correlation_id=correlation_id,
    )


@app.get("/patients/{patient_id}/questions")
async def get_patient_questions(patient_id: str):
    """Proxy to DB Agent to fetch the patient's questionnaire."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.db_agent_url}/patients/{patient_id}/questionnaire",
            )
            if resp.status_code == 200:
                return resp.json()
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"DB Agent returned {resp.status_code}",
            )
    except httpx.HTTPError as exc:
        logger.exception("get_patient_questions.error", patient_id=patient_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

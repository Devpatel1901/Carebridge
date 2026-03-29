from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from shared.cache import cache
from shared.db.engine import create_all_tables, get_db, init_db
from services.db_agent.seed_demo import seed_demo_patients_if_empty
from shared.events.bus import event_bus
from shared.events.contracts import AppointmentConfirmed, JobType, ScheduleEvent
from shared.logging import CorrelationIdMiddleware, get_logger, setup_logging

from services.db_agent import crud
from services.db_agent.config import SERVICE_NAME, get_db_agent_settings
from shared.schemas.models import (
    DoctorScheduleFollowupRequest,
    DoctorScheduleFollowupResponse,
    FollowupJobStatusPatch,
)
from services.db_agent.handlers import (
    handle_alert_event,
    handle_patient_response_event,
    handle_patient_state_upsert,
    handle_schedule_event,
)

setup_logging()
logger = get_logger("db_agent.main")
settings = get_db_agent_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("db_agent_starting")
    await event_bus.connect()
    await cache.connect()
    await init_db()
    await create_all_tables()
    await seed_demo_patients_if_empty()

    await event_bus.subscribe(
        "patient_state_upsert",
        handle_patient_state_upsert,
        queue_name="db_agent.patient_state_upsert",
    )
    await event_bus.subscribe(
        "alert_event",
        handle_alert_event,
        queue_name="db_agent.alert_event",
    )
    await event_bus.subscribe(
        "schedule_event",
        handle_schedule_event,
        queue_name="db_agent.schedule_event",
    )
    await event_bus.subscribe(
        "patient_response_event",
        handle_patient_response_event,
        queue_name="db_agent.patient_response_event",
    )

    logger.info("db_agent_ready")
    yield

    await event_bus.disconnect()
    await cache.disconnect()
    logger.info("db_agent_stopped")


app = FastAPI(
    title="CareBridge DB Agent",
    version="1.0.0",
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
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

@app.get("/patients")
async def list_patients(
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await crud.get_all_patients(session)


@app.get("/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    detail = await crud.get_patient_detail(session, patient_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return detail


_EASTERN = ZoneInfo("America/New_York")


@app.post(
    "/patients/{patient_id}/schedule-followup",
    response_model=DoctorScheduleFollowupResponse,
)
async def schedule_doctor_followup(
    patient_id: str,
    body: DoctorScheduleFollowupRequest,
    session: AsyncSession = Depends(get_db),
) -> DoctorScheduleFollowupResponse:
    """Publish schedule_event (same pipeline as Brain) so followup_jobs + scheduler run."""
    detail = await crud.get_patient_detail(session, patient_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    try:
        local_naive = datetime.strptime(
            f"{body.eastern_date.strip()} {body.eastern_time.strip()}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid eastern_date (YYYY-MM-DD) or eastern_time (HH:MM).",
        ) from exc

    at_local = local_naive.replace(tzinfo=_EASTERN)
    at = at_local.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if at < now - timedelta(minutes=5):
        raise HTTPException(
            status_code=400,
            detail="Scheduled time cannot be more than 5 minutes in the past.",
        )

    cid = str(uuid.uuid4())
    event = ScheduleEvent(
        patient_id=patient_id,
        correlation_id=cid,
        source_service=SERVICE_NAME,
        job_type=JobType.FOLLOWUP,
        scheduled_at=at,
        metadata={"source": "doctor_ui", "from_response_chain": False},
    )
    await event_bus.publish(
        "schedule_event",
        event,
        correlation_id=cid,
        source_service=SERVICE_NAME,
    )
    logger.info(
        "doctor_schedule_followup_published",
        patient_id=patient_id,
        correlation_id=cid,
        scheduled_at_utc=str(at),
    )
    return DoctorScheduleFollowupResponse(correlation_id=cid, scheduled_at=at)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@app.get("/alerts")
async def list_alerts(
    severity: str | None = Query(default=None),
    acknowledged: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await crud.get_alerts(session, severity=severity, acknowledged=acknowledged)


@app.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    alert = await crud.acknowledge_alert(session, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {
        "id": alert.id,
        "acknowledged": alert.acknowledged,
        "message": "Alert acknowledged",
    }


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

@app.get("/patients/{patient_id}/timeline")
async def patient_timeline(
    patient_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await crud.get_patient_timeline(session, patient_id)


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

@app.get("/appointments")
async def list_appointments(
    doctor_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await crud.get_appointments(session, doctor_id=doctor_id)


class CreateAppointmentRequest(BaseModel):
    patient_id: str
    appointment_type: str = "followup"
    status: str = "pending_confirmation"
    notes: str | None = None
    doctor_id: str | None = None
    doctor_name: str | None = None


@app.post("/appointments")
async def create_appointment(
    body: CreateAppointmentRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    appt = await crud.create_appointment(session, body.model_dump())
    return {
        "id": appt.id,
        "patient_id": appt.patient_id,
        "status": appt.status,
        "appointment_type": appt.appointment_type,
    }


class ConfirmAppointmentRequest(BaseModel):
    slot_id: str
    appointment_id: str
    patient_id: str


@app.post("/appointments/confirm")
async def confirm_appointment(
    body: ConfirmAppointmentRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await crud.confirm_appointment_slot(
        session,
        slot_id=body.slot_id,
        appointment_id=body.appointment_id,
        patient_id=body.patient_id,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Slot already booked — please choose another.")
    await event_bus.publish(
        "appointment_confirmed",
        AppointmentConfirmed(
            patient_id=result["patient_id"],
            appointment_id=result["appointment_id"],
            scheduled_at=result["scheduled_at"],
            doctor_name=result["doctor_name"] or "",
            source_service=SERVICE_NAME,
        ),
    )
    return result


class UpdateAppointmentRequest(BaseModel):
    status: str | None = None
    notes: str | None = None
    scheduled_at: str | None = None
    doctor_id: str | None = None
    doctor_name: str | None = None


@app.patch("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    body: UpdateAppointmentRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    appt = await crud.update_appointment(session, appointment_id, updates)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {
        "id": appt.id,
        "patient_id": appt.patient_id,
        "status": appt.status,
        "notes": appt.notes,
        "doctor_name": appt.doctor_name,
        "scheduled_at": appt.scheduled_at.isoformat() if appt.scheduled_at else None,
    }


# ---------------------------------------------------------------------------
# Doctor availability
# ---------------------------------------------------------------------------

@app.get("/doctors/availability")
async def get_doctor_availability(
    urgency: str = Query(default="medium"),
    limit: int = Query(default=3, ge=1, le=10),
    doctor_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await crud.get_available_slots(session, urgency=urgency, limit=limit, doctor_id=doctor_id)


@app.get("/doctors")
async def list_doctors(
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    from sqlalchemy import text
    result = await session.execute(text("SELECT id, name, specialty FROM doctors ORDER BY name"))
    return [{"id": r[0], "name": r[1], "specialty": r[2]} for r in result]


# ---------------------------------------------------------------------------
# Questionnaire
# ---------------------------------------------------------------------------

@app.get("/patients/{patient_id}/questionnaire")
async def get_questionnaire(
    patient_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    q = await crud.get_patient_questionnaire(session, patient_id)
    if q is None:
        raise HTTPException(status_code=404, detail="No questionnaire found")
    return q


# ---------------------------------------------------------------------------
# Follow-up jobs
# ---------------------------------------------------------------------------

@app.get("/followup-jobs")
async def list_followup_jobs(
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await crud.get_followup_jobs(session, status=status)


@app.patch("/followup-jobs/by-correlation/{correlation_id}")
async def patch_followup_job_by_correlation(
    correlation_id: str,
    body: FollowupJobStatusPatch,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    job = await crud.update_followup_job_by_correlation(
        session,
        correlation_id,
        status=body.status,
        executed_at=body.executed_at,
        completed_at=body.completed_at,
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Follow-up job not found")
    return {
        "id": job.id,
        "patient_id": job.patient_id,
        "status": job.status,
        "executed_at": job.executed_at,
        "completed_at": job.completed_at,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.db_agent.main:app",
        host="0.0.0.0",
        port=settings.db_agent_port,
        reload=True,
    )

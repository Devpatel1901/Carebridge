from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from shared.cache import cache
from shared.db.engine import create_all_tables, get_db, init_db
from services.db_agent.seed_demo import seed_demo_patients_if_empty
from shared.events.bus import event_bus
from shared.logging import CorrelationIdMiddleware, get_logger, setup_logging

from services.db_agent import crud
from services.db_agent.config import SERVICE_NAME, get_db_agent_settings
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
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await crud.get_appointments(session)


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

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from fastapi import FastAPI, HTTPException

from services.scheduler.config import SERVICE_NAME, SERVICE_PORT, scheduler_settings
from services.scheduler.jobs import trigger_followup
from shared.events.bus import event_bus
from shared.events.contracts import JobType, ScheduleEvent
from shared.logging import CorrelationIdMiddleware, get_logger, setup_logging

setup_logging()
logger = get_logger(SERVICE_NAME)

# Allow follow-up jobs to run even if the event loop was busy (Docker, GC) — default grace is tiny
# and APScheduler will skip the job entirely ("missed by …") when late by even ~30s.
ap_scheduler = AsyncIOScheduler(
    job_defaults={
        "misfire_grace_time": 600,
        "coalesce": True,
    }
)


# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------

async def handle_schedule_event(envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload", {})
    event = ScheduleEvent(**payload)
    settings = scheduler_settings.settings
    env_correlation_id = str(envelope.get("correlation_id") or "").strip()

    logger.info(
        "schedule_event_received",
        patient_id=event.patient_id,
        job_type=event.job_type,
        scheduled_at=str(event.scheduled_at),
        correlation_id=env_correlation_id or None,
    )

    if event.job_type == JobType.FOLLOWUP:
        from_response_chain = event.metadata.get("from_response_chain", False)
        if settings.demo_mode and not from_response_chain:
            # Align with Brain: DB stores Brain's scheduled_at (minute-scale in demo). The scheduler
            # must use the same instant, not a separate DEMO_FOLLOWUP_DELAY_SECONDS, or the UI and
            # APScheduler disagree and calls appear "missing" or early.
            if event.scheduled_at is not None:
                run_date = event.scheduled_at
                if run_date.tzinfo is None:
                    run_date = run_date.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if run_date <= now:
                    run_date = now + timedelta(seconds=60)
                logger.info(
                    "demo_mode_schedule_from_brain",
                    patient_id=event.patient_id,
                    run_date=str(run_date),
                )
            else:
                delay_sec = max(60, int(getattr(settings, "demo_followup_delay_seconds", 240)))
                run_date = datetime.now(timezone.utc) + timedelta(seconds=delay_sec)
                logger.info(
                    "demo_mode_schedule_fallback_seconds",
                    patient_id=event.patient_id,
                    run_date=str(run_date),
                    delay_seconds=delay_sec,
                )
        else:
            run_date = event.scheduled_at or (datetime.now(timezone.utc) + timedelta(hours=24))
            if run_date.tzinfo is None:
                run_date = run_date.replace(tzinfo=timezone.utc)

        job_id_suffix = env_correlation_id or run_date.isoformat()
        ap_scheduler.add_job(
            trigger_followup,
            trigger=DateTrigger(run_date=run_date),
            kwargs={
                "patient_id": event.patient_id,
                "settings": settings,
                "schedule_correlation_id": env_correlation_id or None,
            },
            id=f"followup_{event.patient_id}_{job_id_suffix}",
            replace_existing=False,
            name=f"Followup for {event.patient_id}",
        )
        logger.info(
            "job_scheduled",
            patient_id=event.patient_id,
            job_type="followup",
            run_date=str(run_date),
        )

    elif event.job_type == JobType.APPOINTMENT:
        logger.info(
            "appointment_event_received",
            patient_id=event.patient_id,
            metadata=event.metadata,
        )


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting", service=SERVICE_NAME, port=SERVICE_PORT)
    await event_bus.connect()
    await event_bus.subscribe(
        "schedule_event",
        handle_schedule_event,
        queue_name="scheduler_schedule_event_queue",
    )
    ap_scheduler.start()
    logger.info("apscheduler_started")
    yield
    ap_scheduler.shutdown(wait=False)
    await event_bus.disconnect()
    logger.info("stopped", service=SERVICE_NAME)


app = FastAPI(
    title="CareBridge Scheduler",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(CorrelationIdMiddleware)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    jobs = ap_scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]


@app.post("/trigger/{patient_id}")
async def manual_trigger(patient_id: str) -> dict[str, Any]:
    settings = scheduler_settings.settings
    # Cancel any pending auto-scheduled jobs for this patient so it doesn't double-fire
    for job in ap_scheduler.get_jobs():
        if patient_id in job.id:
            ap_scheduler.remove_job(job.id)
            logger.info("cancelled_pending_job", job_id=job.id, patient_id=patient_id)
    try:
        call_result = await trigger_followup(patient_id, settings)
    except Exception as exc:
        logger.exception("manual_trigger_failed", patient_id=patient_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "status": "triggered",
        "patient_id": patient_id,
        "call": call_result,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": SERVICE_NAME}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)

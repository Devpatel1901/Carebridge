from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.db.models import (
    Alert,
    Appointment,
    AuditLog,
    DischargeSummary,
    EventStore,
    FollowupJob,
    Medication,
    Patient,
    PatientInteraction,
    Questionnaire,
)
from shared.logging import get_logger

logger = get_logger("db_agent.crud")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _age_from_dob(dob: str | None) -> int | None:
    """Compute age from ISO date string (YYYY-MM-DD)."""
    if not dob or len(dob) < 10:
        return None
    try:
        from datetime import date

        born = date.fromisoformat(dob[:10])
        today = date.today()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return max(0, age)
    except ValueError:
        return None


def _ward_from_appointments(appointments: list[Any]) -> str:
    """Prefer latest appointment with non-empty notes (seed stores ward/bed in notes)."""
    if not appointments:
        return "—"
    sorted_ap = sorted(
        appointments,
        key=lambda a: a.created_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    for a in sorted_ap:
        notes = getattr(a, "notes", None)
        if notes and str(notes).strip():
            return str(notes).strip()
    return "—"


def _id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Patient
# ---------------------------------------------------------------------------

async def upsert_patient(
    session: AsyncSession,
    patient_data: dict[str, Any],
) -> Patient:
    patient_id = patient_data.get("patient_id") or patient_data.get("id") or _id()
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()

    demographics = patient_data.get("demographics", {})
    if patient is None:
        patient = Patient(
            id=patient_id,
            name=demographics.get("name", ""),
            phone=demographics.get("phone", ""),
            dob=demographics.get("dob"),
            email=demographics.get("email"),
            status="active",
            risk_level=patient_data.get("risk_level", "low"),
        )
        session.add(patient)
        logger.info("patient_created", patient_id=patient_id)
    else:
        if demographics.get("name"):
            patient.name = demographics["name"]
        if demographics.get("phone"):
            patient.phone = demographics["phone"]
        if demographics.get("dob"):
            patient.dob = demographics["dob"]
        if demographics.get("email"):
            patient.email = demographics["email"]
        if patient_data.get("risk_level"):
            patient.risk_level = patient_data["risk_level"]
        patient.updated_at = _now()
        logger.info("patient_updated", patient_id=patient_id)

    await session.flush()
    return patient


# ---------------------------------------------------------------------------
# Discharge summary
# ---------------------------------------------------------------------------

async def create_discharge_summary(
    session: AsyncSession,
    patient_id: str,
    discharge_data: dict[str, Any],
) -> DischargeSummary:
    ds = DischargeSummary(
        id=_id(),
        patient_id=patient_id,
        diagnosis=discharge_data.get("diagnosis", ""),
        procedures=discharge_data.get("procedures"),
        discharge_date=discharge_data.get("discharge_date"),
        instructions=discharge_data.get("instructions"),
        raw_text=discharge_data.get("raw_text", ""),
    )
    session.add(ds)
    await session.flush()
    logger.info("discharge_summary_created", patient_id=patient_id, ds_id=ds.id)
    return ds


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------

async def create_medications(
    session: AsyncSession,
    patient_id: str,
    medications_list: list[dict[str, Any]],
) -> list[Medication]:
    created: list[Medication] = []
    for med_data in medications_list:
        med = Medication(
            id=_id(),
            patient_id=patient_id,
            name=med_data.get("name", ""),
            dosage=med_data.get("dosage", ""),
            frequency=med_data.get("frequency", ""),
        )
        session.add(med)
        created.append(med)
    await session.flush()
    logger.info(
        "medications_created", patient_id=patient_id, count=len(created)
    )
    return created


# ---------------------------------------------------------------------------
# Questionnaire
# ---------------------------------------------------------------------------

async def create_questionnaire(
    session: AsyncSession,
    patient_id: str,
    questions_json: str,
    diagnosis_context: str,
) -> Questionnaire:
    q = Questionnaire(
        id=_id(),
        patient_id=patient_id,
        questions_json=questions_json,
        diagnosis_context=diagnosis_context,
    )
    session.add(q)
    await session.flush()
    logger.info("questionnaire_created", patient_id=patient_id, q_id=q.id)
    return q


# ---------------------------------------------------------------------------
# Patient interaction
# ---------------------------------------------------------------------------

async def create_interaction(
    session: AsyncSession,
    data: dict[str, Any],
) -> PatientInteraction:
    interaction = PatientInteraction(
        id=data.get("id") or _id(),
        patient_id=data["patient_id"],
        interaction_type=data.get("interaction_type", "followup"),
        channel=data.get("channel", "sms"),
        questionnaire_id=data.get("questionnaire_id"),
        questions_json=data.get("questions_json"),
        responses_json=data.get("responses_json"),
        raw_transcript=data.get("raw_transcript"),
        twilio_sid=data.get("twilio_sid"),
    )
    session.add(interaction)
    await session.flush()
    logger.info("interaction_created", interaction_id=interaction.id)
    return interaction


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

async def create_alert(
    session: AsyncSession,
    data: dict[str, Any],
) -> Alert:
    alert = Alert(
        id=data.get("id") or _id(),
        patient_id=data["patient_id"],
        alert_type=data.get("alert_type", "general"),
        severity=data.get("severity", "medium"),
        message=data.get("message", ""),
        acknowledged=data.get("acknowledged", False),
    )
    session.add(alert)
    await session.flush()
    logger.info("alert_created", alert_id=alert.id, patient_id=alert.patient_id)
    return alert


# ---------------------------------------------------------------------------
# Appointment
# ---------------------------------------------------------------------------

async def create_appointment(
    session: AsyncSession,
    data: dict[str, Any],
) -> Appointment:
    scheduled_at = data.get("scheduled_at")
    if isinstance(scheduled_at, str):
        scheduled_at = datetime.fromisoformat(scheduled_at)

    appt = Appointment(
        id=data.get("id") or _id(),
        patient_id=data["patient_id"],
        appointment_type=data.get("appointment_type", "followup"),
        scheduled_at=scheduled_at,
        status=data.get("status", "scheduled"),
        notes=data.get("notes"),
    )
    session.add(appt)
    await session.flush()
    logger.info("appointment_created", appt_id=appt.id, patient_id=appt.patient_id)
    return appt


# ---------------------------------------------------------------------------
# Follow-up job
# ---------------------------------------------------------------------------

async def create_followup_job(
    session: AsyncSession,
    data: dict[str, Any],
) -> FollowupJob:
    scheduled_at = data.get("scheduled_at")
    if isinstance(scheduled_at, str):
        scheduled_at = datetime.fromisoformat(scheduled_at)

    job = FollowupJob(
        id=data.get("id") or _id(),
        patient_id=data["patient_id"],
        job_type=data.get("job_type", "followup"),
        scheduled_at=scheduled_at,
        status=data.get("status", "pending"),
    )
    session.add(job)
    await session.flush()
    logger.info("followup_job_created", job_id=job.id, patient_id=job.patient_id)
    return job


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

async def log_audit(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
    action: str,
    changes: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        id=_id(),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes_json=json.dumps(changes) if changes else None,
        correlation_id=correlation_id,
    )
    session.add(entry)
    await session.flush()
    return entry


# ---------------------------------------------------------------------------
# Event store (idempotency via correlation_id)
# ---------------------------------------------------------------------------

async def store_event(
    session: AsyncSession,
    event_type: str,
    payload_json: str,
    correlation_id: str | None = None,
    source_service: str | None = None,
) -> EventStore | None:
    """Store a raw event. Returns None if a duplicate correlation_id already exists."""
    if correlation_id:
        existing = await session.execute(
            select(EventStore).where(
                EventStore.correlation_id == correlation_id,
                EventStore.event_type == event_type,
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.info(
                "duplicate_event_skipped",
                event_type=event_type,
                correlation_id=correlation_id,
            )
            return None

    evt = EventStore(
        id=_id(),
        event_type=event_type,
        payload_json=payload_json,
        correlation_id=correlation_id,
        source_service=source_service,
    )
    session.add(evt)
    await session.flush()
    return evt


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

async def get_all_patients(session: AsyncSession) -> list[dict[str, Any]]:
    """List patients with dashboard fields: reason (latest diagnosis), ward (appointment notes), age."""
    result = await session.execute(
        select(Patient)
        .options(
            selectinload(Patient.discharge_summaries),
            selectinload(Patient.appointments),
        )
        .order_by(Patient.created_at.desc())
    )
    patients = result.scalars().all()
    rows: list[dict[str, Any]] = []
    for p in patients:
        latest_ds = None
        if p.discharge_summaries:
            latest_ds = max(p.discharge_summaries, key=lambda d: d.created_at)
        reason = (latest_ds.diagnosis if latest_ds else None) or "—"
        ward = _ward_from_appointments(list(p.appointments))
        rows.append(
            {
                "id": p.id,
                "name": p.name,
                "phone": p.phone,
                "dob": p.dob,
                "status": p.status,
                "risk_level": p.risk_level,
                "created_at": p.created_at,
                "reason": reason,
                "ward": ward,
                "age": _age_from_dob(p.dob),
            }
        )
    return rows


async def get_patient_detail(
    session: AsyncSession, patient_id: str
) -> dict[str, Any] | None:
    result = await session.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        .options(
            selectinload(Patient.discharge_summaries),
            selectinload(Patient.medications),
            selectinload(Patient.questionnaires),
            selectinload(Patient.interactions),
            selectinload(Patient.alerts),
            selectinload(Patient.appointments),
        )
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        return None

    latest_ds = (
        max(patient.discharge_summaries, key=lambda d: d.created_at)
        if patient.discharge_summaries
        else None
    )

    latest_q = (
        max(patient.questionnaires, key=lambda q: q.generated_at)
        if patient.questionnaires
        else None
    )

    return {
        "id": patient.id,
        "name": patient.name,
        "phone": patient.phone,
        "dob": patient.dob,
        "email": patient.email,
        "status": patient.status,
        "risk_level": patient.risk_level,
        "created_at": patient.created_at,
        "discharge_summary": (
            {
                "id": latest_ds.id,
                "diagnosis": latest_ds.diagnosis,
                "procedures": latest_ds.procedures,
                "discharge_date": latest_ds.discharge_date,
                "instructions": latest_ds.instructions,
                "raw_text": latest_ds.raw_text,
                "created_at": latest_ds.created_at,
            }
            if latest_ds
            else None
        ),
        "medications": [
            {
                "id": m.id,
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "created_at": m.created_at,
            }
            for m in patient.medications
        ],
        "questionnaire": (
            {
                "id": latest_q.id,
                "questions": json.loads(latest_q.questions_json),
                "diagnosis_context": latest_q.diagnosis_context,
                "generated_at": latest_q.generated_at,
            }
            if latest_q
            else None
        ),
        "interactions": [
            {
                "id": i.id,
                "interaction_type": i.interaction_type,
                "channel": i.channel,
                "questionnaire_id": i.questionnaire_id,
                "responses": (
                    json.loads(i.responses_json) if i.responses_json else None
                ),
                "created_at": i.created_at,
            }
            for i in sorted(
                patient.interactions, key=lambda x: x.created_at, reverse=True
            )
        ],
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "acknowledged": a.acknowledged,
                "created_at": a.created_at,
            }
            for a in sorted(patient.alerts, key=lambda x: x.created_at, reverse=True)
        ],
        "appointments": [
            {
                "id": ap.id,
                "appointment_type": ap.appointment_type,
                "scheduled_at": ap.scheduled_at,
                "status": ap.status,
                "notes": ap.notes,
                "created_at": ap.created_at,
            }
            for ap in sorted(
                patient.appointments, key=lambda x: x.created_at, reverse=True
            )
        ],
    }


async def get_alerts(
    session: AsyncSession,
    severity: str | None = None,
    acknowledged: bool | None = None,
) -> list[dict[str, Any]]:
    stmt = select(Alert).options(selectinload(Alert.patient))
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    if acknowledged is not None:
        stmt = stmt.where(Alert.acknowledged == acknowledged)
    stmt = stmt.order_by(Alert.created_at.desc())

    result = await session.execute(stmt)
    alerts = result.scalars().all()
    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "patient_name": a.patient.name if a.patient else None,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.message,
            "acknowledged": a.acknowledged,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


async def get_patient_timeline(
    session: AsyncSession, patient_id: str
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    # Interactions
    result = await session.execute(
        select(PatientInteraction)
        .where(PatientInteraction.patient_id == patient_id)
    )
    for i in result.scalars().all():
        entries.append({
            "id": i.id,
            "event_type": "interaction",
            "patient_id": i.patient_id,
            "summary": f"{i.interaction_type} via {i.channel}",
            "created_at": i.created_at,
            "details": {
                "channel": i.channel,
                "interaction_type": i.interaction_type,
                "questionnaire_id": i.questionnaire_id,
            },
        })

    # Alerts
    result = await session.execute(
        select(Alert).where(Alert.patient_id == patient_id)
    )
    for a in result.scalars().all():
        entries.append({
            "id": a.id,
            "event_type": "alert",
            "patient_id": a.patient_id,
            "summary": f"[{a.severity}] {a.alert_type}: {a.message}",
            "created_at": a.created_at,
            "details": {
                "alert_type": a.alert_type,
                "severity": a.severity,
                "acknowledged": a.acknowledged,
            },
        })

    # Appointments
    result = await session.execute(
        select(Appointment).where(Appointment.patient_id == patient_id)
    )
    for ap in result.scalars().all():
        entries.append({
            "id": ap.id,
            "event_type": "appointment",
            "patient_id": ap.patient_id,
            "summary": f"{ap.appointment_type} — {ap.status}",
            "created_at": ap.created_at,
            "details": {
                "appointment_type": ap.appointment_type,
                "scheduled_at": ap.scheduled_at.isoformat() if ap.scheduled_at else None,
                "status": ap.status,
                "notes": ap.notes,
            },
        })

    # Audit logs
    result = await session.execute(
        select(AuditLog).where(AuditLog.entity_id == patient_id)
    )
    for log in result.scalars().all():
        entries.append({
            "id": log.id,
            "event_type": "audit",
            "patient_id": patient_id,
            "summary": f"{log.action} on {log.entity_type}",
            "created_at": log.created_at,
            "details": {
                "entity_type": log.entity_type,
                "action": log.action,
                "changes": json.loads(log.changes_json) if log.changes_json else None,
            },
        })

    entries.sort(key=lambda e: e["created_at"] or _now(), reverse=True)
    return entries


async def get_appointments(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .order_by(Appointment.created_at.desc())
    )
    appointments = result.scalars().all()
    return [
        {
            "id": ap.id,
            "patient_id": ap.patient_id,
            "patient_name": ap.patient.name if ap.patient else None,
            "appointment_type": ap.appointment_type,
            "scheduled_at": ap.scheduled_at,
            "status": ap.status,
            "notes": ap.notes,
            "created_at": ap.created_at,
        }
        for ap in appointments
    ]


async def acknowledge_alert(session: AsyncSession, alert_id: str) -> Alert | None:
    result = await session.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        return None
    alert.acknowledged = True
    await session.flush()
    logger.info("alert_acknowledged", alert_id=alert_id)
    return alert


async def get_patient_questionnaire(
    session: AsyncSession, patient_id: str
) -> dict[str, Any] | None:
    result = await session.execute(
        select(Questionnaire)
        .where(Questionnaire.patient_id == patient_id)
        .order_by(Questionnaire.generated_at.desc())
        .limit(1)
    )
    q = result.scalar_one_or_none()
    if q is None:
        return None
    return {
        "id": q.id,
        "questionnaire_id": q.id,
        "patient_id": q.patient_id,
        "questions": json.loads(q.questions_json),
        "diagnosis_context": q.diagnosis_context,
        "generated_at": q.generated_at,
    }


async def get_followup_jobs(
    session: AsyncSession, status: str | None = None
) -> list[dict[str, Any]]:
    stmt = select(FollowupJob).options(selectinload(FollowupJob.patient))
    if status is not None:
        stmt = stmt.where(FollowupJob.status == status)
    stmt = stmt.order_by(FollowupJob.created_at.desc())

    result = await session.execute(stmt)
    jobs = result.scalars().all()
    return [
        {
            "id": j.id,
            "patient_id": j.patient_id,
            "patient_name": j.patient.name if j.patient else None,
            "job_type": j.job_type,
            "scheduled_at": j.scheduled_at,
            "status": j.status,
            "executed_at": j.executed_at,
            "created_at": j.created_at,
        }
        for j in jobs
    ]

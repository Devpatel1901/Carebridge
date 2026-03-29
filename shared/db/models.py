from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    name: Mapped[str] = mapped_column(String(255))
    dob: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="active")
    risk_level: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    discharge_summaries: Mapped[list[DischargeSummary]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    medications: Mapped[list[Medication]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    questionnaires: Mapped[list[Questionnaire]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    interactions: Mapped[list[PatientInteraction]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    followup_jobs: Mapped[list[FollowupJob]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class DischargeSummary(Base):
    __tablename__ = "discharge_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    diagnosis: Mapped[str] = mapped_column(Text)
    procedures: Mapped[str | None] = mapped_column(Text)
    discharge_date: Mapped[str | None] = mapped_column(String(20))
    instructions: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    patient: Mapped[Patient] = relationship(back_populates="discharge_summaries")


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    name: Mapped[str] = mapped_column(String(255))
    dosage: Mapped[str] = mapped_column(String(100))
    frequency: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    patient: Mapped[Patient] = relationship(back_populates="medications")


class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    questions_json: Mapped[str] = mapped_column(Text, default="[]")
    diagnosis_context: Mapped[str] = mapped_column(Text, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    patient: Mapped[Patient] = relationship(back_populates="questionnaires")


class PatientInteraction(Base):
    __tablename__ = "patient_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    interaction_type: Mapped[str] = mapped_column(String(50))
    channel: Mapped[str] = mapped_column(String(20), default="sms")
    questionnaire_id: Mapped[str | None] = mapped_column(String(36))
    questions_json: Mapped[str | None] = mapped_column(Text)
    responses_json: Mapped[str | None] = mapped_column(Text)
    raw_transcript: Mapped[str | None] = mapped_column(Text)
    twilio_sid: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    patient: Mapped[Patient] = relationship(back_populates="interactions")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text, default="")
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    patient: Mapped[Patient] = relationship(back_populates="alerts")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    appointment_type: Mapped[str] = mapped_column(String(50))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    patient: Mapped[Patient] = relationship(back_populates="appointments")


class FollowupJob(Base):
    __tablename__ = "followup_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"))
    job_type: Mapped[str] = mapped_column(String(50))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    correlation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    patient: Mapped[Patient] = relationship(back_populates="followup_jobs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(50))
    changes_json: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class EventStore(Base):
    __tablename__ = "event_store"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_id)
    event_type: Mapped[str] = mapped_column(String(100))
    payload_json: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(36))
    source_service: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

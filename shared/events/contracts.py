from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

import uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseEvent(BaseModel):
    correlation_id: str = Field(default_factory=_uuid)
    event_type: str = ""
    timestamp: datetime = Field(default_factory=_utcnow)
    source_service: str = "unknown"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    FEVER = "fever"
    CHEST_PAIN = "chest_pain"
    MISSED_MEDS = "missed_meds"
    DIZZINESS = "dizziness"
    GENERAL = "general"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobType(str, Enum):
    FOLLOWUP = "followup"
    APPOINTMENT = "appointment"


class DecisionType(str, Enum):
    STABLE = "stable"
    FOLLOWUP_NEEDED = "followup_needed"
    ALERT = "alert"
    ESCALATION = "escalation"
    APPOINTMENT_REQUIRED = "appointment_required"


# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------

class QuestionItem(BaseModel):
    id: str
    text: str
    question_type: str = "open"  # open, yes_no, scale
    relevance: str = ""


class ResponseItem(BaseModel):
    question_id: str
    question_text: str
    answer: str
    normalized: str | None = None
    clinical_flags: list[str] = []


class DemographicsData(BaseModel):
    name: str
    dob: str | None = None
    phone: str
    email: str | None = None


class DischargeData(BaseModel):
    diagnosis: str
    procedures: str | None = None
    discharge_date: str | None = None
    instructions: str | None = None
    raw_text: str = ""


class MedicationData(BaseModel):
    name: str
    dosage: str
    frequency: str


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class PatientStateUpsert(BaseEvent):
    event_type: str = "patient_state_upsert"
    patient_id: str
    demographics: DemographicsData
    discharge_data: DischargeData
    medications: list[MedicationData] = []
    risk_level: RiskLevel = RiskLevel.LOW
    generated_questions: list[QuestionItem] = []


class PatientResponseEvent(BaseEvent):
    event_type: str = "patient_response_event"
    patient_id: str
    interaction_id: str = Field(default_factory=_uuid)
    questionnaire_id: str | None = None
    responses: list[ResponseItem] = []
    channel: str = "sms"  # sms or voice
    twilio_sid: str | None = None


class AlertEvent(BaseEvent):
    event_type: str = "alert_event"
    patient_id: str
    alert_type: AlertType = AlertType.GENERAL
    severity: Severity = Severity.MEDIUM
    message: str = ""


class ScheduleEvent(BaseEvent):
    event_type: str = "schedule_event"
    patient_id: str
    job_type: JobType = JobType.FOLLOWUP
    scheduled_at: datetime | None = None
    metadata: dict[str, Any] = {}


class PatientRecordUpdated(BaseEvent):
    event_type: str = "patient_record_updated"
    patient_id: str
    updated_fields: list[str] = []

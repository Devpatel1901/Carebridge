from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from shared.events.contracts import (
    AlertType,
    DecisionType,
    MedicationData,
    QuestionItem,
    ResponseItem,
    RiskLevel,
    Severity,
)


# ---------------------------------------------------------------------------
# Request / Response schemas for REST APIs
# ---------------------------------------------------------------------------

class DischargeIntakeRequest(BaseModel):
    patient_name: str
    patient_phone: str
    patient_dob: str | None = None
    patient_email: str | None = None
    discharge_summary_text: str
    existing_patient_id: str | None = Field(
        default=None,
        description="When set, Brain intake uses this patient id (upsert) instead of a new UUID.",
    )


class DischargeIntakeResponse(BaseModel):
    patient_id: str
    risk_level: RiskLevel
    decision: DecisionType
    generated_questions: list[QuestionItem]
    correlation_id: str


class EvaluateResponseRequest(BaseModel):
    patient_id: str
    responses: list[ResponseItem]
    channel: str = "voice"
    twilio_sid: str | None = None
    questionnaire_id: str | None = None


class EvaluateResponseResult(BaseModel):
    patient_id: str
    risk_level: RiskLevel
    decision: DecisionType
    alerts: list[dict[str, Any]] = []
    correlation_id: str


class InitiateCallRequest(BaseModel):
    patient_id: str


class PatientSummary(BaseModel):
    id: str
    name: str
    phone: str
    status: str
    risk_level: str | None = None
    created_at: datetime | None = None


class PatientDetail(BaseModel):
    id: str
    name: str
    phone: str
    dob: str | None = None
    email: str | None = None
    status: str
    risk_level: str | None = None
    created_at: datetime | None = None
    discharge_summary: dict[str, Any] | None = None
    medications: list[dict[str, Any]] = []
    questionnaire: dict[str, Any] | None = None
    interactions: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    appointments: list[dict[str, Any]] = []


class AlertOut(BaseModel):
    id: str
    patient_id: str
    patient_name: str | None = None
    alert_type: str
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime | None = None


class AppointmentOut(BaseModel):
    id: str
    patient_id: str
    patient_name: str | None = None
    appointment_type: str
    scheduled_at: datetime | None = None
    status: str
    notes: str | None = None
    created_at: datetime | None = None


class TimelineEntry(BaseModel):
    id: str
    event_type: str
    patient_id: str
    patient_name: str | None = None
    summary: str
    created_at: datetime | None = None
    details: dict[str, Any] = {}

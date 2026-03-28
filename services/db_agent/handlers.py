from __future__ import annotations

import json
from typing import Any

from shared.db.engine import get_session_factory
from shared.events.bus import event_bus
from shared.events.contracts import PatientRecordUpdated
from shared.logging import get_logger

from services.db_agent import crud
from services.db_agent.config import SERVICE_NAME

logger = get_logger("db_agent.handlers")


async def _get_session():
    factory = get_session_factory()
    return factory()


# ---------------------------------------------------------------------------
# patient_state_upsert
# ---------------------------------------------------------------------------

async def handle_patient_state_upsert(envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload", {})
    correlation_id = envelope.get("correlation_id", "")
    source_service = envelope.get("source_service", "unknown")

    logger.info(
        "handling_patient_state_upsert",
        patient_id=payload.get("patient_id"),
        correlation_id=correlation_id,
    )

    async with await _get_session() as session:
        async with session.begin():
            stored = await crud.store_event(
                session,
                event_type="patient_state_upsert",
                payload_json=json.dumps(payload),
                correlation_id=correlation_id,
                source_service=source_service,
            )
            if stored is None:
                logger.info(
                    "duplicate_event_ignored",
                    event_type="patient_state_upsert",
                    correlation_id=correlation_id,
                )
                return

            patient = await crud.upsert_patient(session, payload)
            patient_id = patient.id
            updated_fields = ["patient"]

            discharge_data = payload.get("discharge_data")
            if discharge_data:
                await crud.create_discharge_summary(
                    session, patient_id, discharge_data
                )
                updated_fields.append("discharge_summary")

            medications = payload.get("medications", [])
            if medications:
                await crud.create_medications(session, patient_id, medications)
                updated_fields.append("medications")

            questions = payload.get("generated_questions", [])
            if questions:
                diagnosis_context = (
                    discharge_data.get("diagnosis", "") if discharge_data else ""
                )
                await crud.create_questionnaire(
                    session,
                    patient_id,
                    json.dumps(questions),
                    diagnosis_context,
                )
                updated_fields.append("questionnaire")

            await crud.log_audit(
                session,
                entity_type="patient",
                entity_id=patient_id,
                action="upsert",
                changes={"updated_fields": updated_fields},
                correlation_id=correlation_id,
            )

    await event_bus.publish(
        "patient_record_updated",
        PatientRecordUpdated(
            patient_id=patient_id,
            updated_fields=updated_fields,
            correlation_id=correlation_id,
            source_service=SERVICE_NAME,
        ),
        correlation_id=correlation_id,
        source_service=SERVICE_NAME,
    )

    logger.info(
        "patient_state_upsert_complete",
        patient_id=patient_id,
        updated_fields=updated_fields,
    )


# ---------------------------------------------------------------------------
# alert_event
# ---------------------------------------------------------------------------

async def handle_alert_event(envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload", {})
    correlation_id = envelope.get("correlation_id", "")
    source_service = envelope.get("source_service", "unknown")

    logger.info(
        "handling_alert_event",
        patient_id=payload.get("patient_id"),
        correlation_id=correlation_id,
    )

    async with await _get_session() as session:
        async with session.begin():
            stored = await crud.store_event(
                session,
                event_type="alert_event",
                payload_json=json.dumps(payload),
                correlation_id=correlation_id,
                source_service=source_service,
            )
            if stored is None:
                logger.info(
                    "duplicate_event_ignored",
                    event_type="alert_event",
                    correlation_id=correlation_id,
                )
                return

            alert = await crud.create_alert(session, payload)

            await crud.log_audit(
                session,
                entity_type="alert",
                entity_id=alert.id,
                action="created",
                changes={
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                },
                correlation_id=correlation_id,
            )

    patient_id = payload.get("patient_id", "")
    await event_bus.publish(
        "patient_record_updated",
        PatientRecordUpdated(
            patient_id=patient_id,
            updated_fields=["alert"],
            correlation_id=correlation_id,
            source_service=SERVICE_NAME,
        ),
        correlation_id=correlation_id,
        source_service=SERVICE_NAME,
    )

    logger.info("alert_event_complete", alert_id=alert.id)


# ---------------------------------------------------------------------------
# patient_response_event  (store raw Q&A as PatientInteraction)
# ---------------------------------------------------------------------------

async def handle_patient_response_event(envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload", {})
    correlation_id = envelope.get("correlation_id", "")
    source_service = envelope.get("source_service", "unknown")

    patient_id = payload.get("patient_id")
    logger.info(
        "handling_patient_response_event",
        patient_id=patient_id,
        correlation_id=correlation_id,
    )

    async with await _get_session() as session:
        async with session.begin():
            stored = await crud.store_event(
                session,
                event_type="patient_response_event",
                payload_json=json.dumps(payload),
                correlation_id=correlation_id,
                source_service=source_service,
            )
            if stored is None:
                logger.info(
                    "duplicate_event_ignored",
                    event_type="patient_response_event",
                    correlation_id=correlation_id,
                )
                return

            responses = payload.get("responses", [])
            # Build a clean Q&A list: [{question, answer, normalized}]
            qa_list = [
                {
                    "question_id": r.get("question_id"),
                    "question": r.get("question_text"),
                    "answer": r.get("answer"),
                    "normalized": r.get("normalized"),
                }
                for r in responses
            ]

            interaction = await crud.create_interaction(
                session,
                {
                    "patient_id": patient_id,
                    "interaction_type": "followup",
                    "channel": payload.get("channel", "voice"),
                    "questionnaire_id": payload.get("questionnaire_id"),
                    "questions_json": json.dumps(
                        [{"id": r.get("question_id"), "text": r.get("question_text")} for r in responses]
                    ),
                    "responses_json": json.dumps(qa_list),
                    "twilio_sid": payload.get("twilio_sid"),
                },
            )

            await crud.log_audit(
                session,
                entity_type="patient_interaction",
                entity_id=interaction.id,
                action="created",
                changes={"response_count": len(responses), "channel": "voice"},
                correlation_id=correlation_id,
            )

    await event_bus.publish(
        "patient_record_updated",
        PatientRecordUpdated(
            patient_id=patient_id,
            updated_fields=["interaction"],
            correlation_id=correlation_id,
            source_service=SERVICE_NAME,
        ),
        correlation_id=correlation_id,
        source_service=SERVICE_NAME,
    )

    logger.info(
        "patient_response_event_complete",
        patient_id=patient_id,
        interaction_id=interaction.id,
        response_count=len(responses),
    )


# ---------------------------------------------------------------------------
# schedule_event
# ---------------------------------------------------------------------------

async def handle_schedule_event(envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload", {})
    correlation_id = envelope.get("correlation_id", "")
    source_service = envelope.get("source_service", "unknown")
    job_type = payload.get("job_type", "followup")

    logger.info(
        "handling_schedule_event",
        patient_id=payload.get("patient_id"),
        job_type=job_type,
        correlation_id=correlation_id,
    )

    async with await _get_session() as session:
        async with session.begin():
            stored = await crud.store_event(
                session,
                event_type="schedule_event",
                payload_json=json.dumps(payload),
                correlation_id=correlation_id,
                source_service=source_service,
            )
            if stored is None:
                logger.info(
                    "duplicate_event_ignored",
                    event_type="schedule_event",
                    correlation_id=correlation_id,
                )
                return

            entity_type: str
            entity_id: str

            if job_type == "appointment":
                appt_data = {
                    "patient_id": payload["patient_id"],
                    "appointment_type": payload.get("metadata", {}).get(
                        "appointment_type", "followup"
                    ),
                    "scheduled_at": payload.get("scheduled_at"),
                    "notes": payload.get("metadata", {}).get("notes"),
                }
                appt = await crud.create_appointment(session, appt_data)
                entity_type = "appointment"
                entity_id = appt.id
            else:
                job_data = {
                    "patient_id": payload["patient_id"],
                    "job_type": job_type,
                    "scheduled_at": payload.get("scheduled_at"),
                }
                job = await crud.create_followup_job(session, job_data)
                entity_type = "followup_job"
                entity_id = job.id

            await crud.log_audit(
                session,
                entity_type=entity_type,
                entity_id=entity_id,
                action="created",
                changes={"job_type": job_type},
                correlation_id=correlation_id,
            )

    patient_id = payload.get("patient_id", "")
    await event_bus.publish(
        "patient_record_updated",
        PatientRecordUpdated(
            patient_id=patient_id,
            updated_fields=[entity_type],
            correlation_id=correlation_id,
            source_service=SERVICE_NAME,
        ),
        correlation_id=correlation_id,
        source_service=SERVICE_NAME,
    )

    logger.info(
        "schedule_event_complete",
        entity_type=entity_type,
        entity_id=entity_id,
    )

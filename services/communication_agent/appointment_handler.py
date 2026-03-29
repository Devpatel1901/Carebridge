"""RabbitMQ consumer for appointment_booking_request events.

When the Brain Agent decides a patient needs an in-person appointment,
it emits an appointment_booking_request. This handler:
  1. Fetches the patient's phone/name from the DB Agent.
  2. Fetches available doctor slots from the DB Agent.
  3. Creates a pending appointment record in the DB Agent.
  4. Stores the booking session in Redis.
  5. Places an outbound Twilio voice call to the patient.
"""
from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlencode

import httpx

from services.communication_agent.config import comm_settings
from services.communication_agent.ngrok_compat import ngrok_free_skip_warning_params
from services.communication_agent.twilio_client import make_voice_call
from shared.cache import cache
from shared.logging import get_logger

logger = get_logger("communication_agent.appointment_handler")

APPT_SESSION_TTL = 3600  # 1 hour


async def handle_appointment_booking_request(envelope: dict[str, Any]) -> None:
    """Consume appointment_booking_request and initiate a booking voice call."""
    payload = envelope.get("payload", {})
    patient_id = payload.get("patient_id", "")
    urgency = payload.get("urgency", "medium")
    reason = payload.get("reason", "")
    correlation_id = envelope.get("correlation_id", str(uuid.uuid4()))

    logger.info(
        "appointment_booking_request.received",
        patient_id=patient_id,
        urgency=urgency,
        correlation_id=correlation_id,
    )

    settings = comm_settings.settings

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Fetch patient details
        patient_resp = await client.get(f"{settings.db_agent_url}/patients/{patient_id}")
        if patient_resp.status_code != 200:
            logger.error(
                "appointment_booking.patient_fetch_failed",
                patient_id=patient_id,
                status=patient_resp.status_code,
            )
            return
        patient = patient_resp.json()

        patient_phone = patient.get("phone", "")
        patient_name = patient.get("name", "")

        if not patient_phone:
            logger.error("appointment_booking.no_phone", patient_id=patient_id)
            return

        # 2. Fetch available doctor slots
        slots_resp = await client.get(
            f"{settings.db_agent_url}/doctors/availability",
            params={"urgency": urgency, "limit": 3},
        )
        if slots_resp.status_code != 200:
            logger.error(
                "appointment_booking.slots_fetch_failed",
                status=slots_resp.status_code,
            )
            return

        slots = slots_resp.json()
        if not slots:
            logger.warning(
                "appointment_booking.no_slots_available",
                patient_id=patient_id,
                urgency=urgency,
            )
            return

        # 3. Create a pending appointment record
        appt_resp = await client.post(
            f"{settings.db_agent_url}/appointments",
            json={
                "patient_id": patient_id,
                "appointment_type": "followup",
                "status": "pending_confirmation",
                "notes": reason,
            },
        )
        if appt_resp.status_code not in (200, 201):
            logger.error(
                "appointment_booking.create_appt_failed",
                status=appt_resp.status_code,
            )
            return

        appointment_id = appt_resp.json().get("id", "")

    # 4. Store booking session in Redis
    voice_session_id = str(uuid.uuid4())
    session_key = f"appt_session:{voice_session_id}"
    session = {
        "voice_session_id": voice_session_id,
        "patient_id": patient_id,
        "patient_phone": patient_phone,
        "patient_name": patient_name,
        "appointment_id": appointment_id,
        "slots": slots,
        "urgency": urgency,
        "reason": reason,
        "retry_count": 0,
        "correlation_id": correlation_id,
    }
    await cache.set_json(session_key, session, expire_seconds=APPT_SESSION_TTL)

    # 5. Place outbound Twilio call
    base = settings.twilio_webhook_base_url.strip().rstrip("/")
    ngrok_q = ngrok_free_skip_warning_params(base)
    start_q = urlencode({"voice_session_id": voice_session_id, **ngrok_q})
    start_url = f"{base}/webhooks/voice/appointment/start?{start_q}"
    status_url = (
        f"{base}/webhooks/voice/status?{urlencode(ngrok_q)}"
        if ngrok_q
        else f"{base}/webhooks/voice/status"
    )

    try:
        call_sid = await make_voice_call(
            to=patient_phone,
            twiml_url=start_url,
            status_callback_url=status_url,
        )
        session["call_sid"] = call_sid
        await cache.set_json(session_key, session, expire_seconds=APPT_SESSION_TTL)
        logger.info(
            "appointment_booking.call_initiated",
            patient_id=patient_id,
            call_sid=call_sid,
            appointment_id=appointment_id,
            slots_offered=len(slots),
        )
    except Exception:
        logger.exception(
            "appointment_booking.call_failed",
            patient_id=patient_id,
        )

from __future__ import annotations

import httpx

from shared.config import Settings
from shared.logging import get_logger

logger = get_logger("scheduler.jobs")


async def trigger_followup(patient_id: str, settings: Settings) -> None:
    """Call Communication Agent to initiate a follow-up call."""
    logger.info("trigger_followup_start", patient_id=patient_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.comm_agent_url}/initiate-call",
            json={"patient_id": patient_id},
        )

    if response.status_code == 200:
        logger.info(
            "trigger_followup_success",
            patient_id=patient_id,
            result=response.json(),
        )
    else:
        logger.error(
            "trigger_followup_failed",
            patient_id=patient_id,
            status_code=response.status_code,
            detail=response.text,
        )

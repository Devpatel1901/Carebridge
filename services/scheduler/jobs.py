from __future__ import annotations

from typing import Any

import httpx

from shared.config import Settings
from shared.logging import get_logger

logger = get_logger("scheduler.jobs")


async def trigger_followup(patient_id: str, settings: Settings) -> dict[str, Any]:
    """Call Communication Agent to initiate a follow-up call. Returns its JSON body."""
    logger.info("trigger_followup_start", patient_id=patient_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.comm_agent_url}/initiate-call",
            json={"patient_id": patient_id},
        )

    if response.status_code == 200:
        result = response.json()
        logger.info(
            "trigger_followup_success",
            patient_id=patient_id,
            result=result,
        )
        return result

    logger.error(
        "trigger_followup_failed",
        patient_id=patient_id,
        status_code=response.status_code,
        detail=response.text,
    )
    raise RuntimeError(
        f"Communication agent returned {response.status_code}: {response.text}"
    )

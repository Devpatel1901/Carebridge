"""HTTP updates to DB Agent follow-up job rows (schedule_correlation_id)."""
from __future__ import annotations

import asyncio
from datetime import datetime

import httpx

from shared.config import get_settings
from shared.logging import get_logger

logger = get_logger("communication_agent.followup_db")


async def patch_followup_job_status(
    correlation_id: str | None,
    status: str,
    *,
    executed_at: datetime | None = None,
    completed_at: datetime | None = None,
    retries: int = 4,
) -> bool:
    """PATCH /followup-jobs/by-correlation/{id}. Retries briefly if the job row is not visible yet."""
    if not (correlation_id or "").strip():
        return False
    cid = correlation_id.strip()
    settings = get_settings()
    url = f"{settings.db_agent_url.rstrip('/')}/followup-jobs/by-correlation/{cid}"
    payload: dict[str, object] = {"status": status}
    if executed_at is not None:
        payload["executed_at"] = executed_at.isoformat()
    if completed_at is not None:
        payload["completed_at"] = completed_at.isoformat()

    last_exc: BaseException | None = None
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.patch(url, json=payload)
            if r.status_code == 404:
                logger.warning(
                    "followup_job_patch_not_found",
                    correlation_id=cid,
                    attempt=attempt + 1,
                )
                await asyncio.sleep(0.4)
                continue
            r.raise_for_status()
            logger.info(
                "followup_job_patched",
                correlation_id=cid,
                status=status,
            )
            return True
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "followup_job_patch_retry",
                correlation_id=cid,
                attempt=attempt + 1,
                error=str(exc),
            )
            await asyncio.sleep(0.4)
    if last_exc:
        logger.exception(
            "followup_job_patch_failed",
            correlation_id=cid,
        )
    return False

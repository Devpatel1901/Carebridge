"""Ensure future doctor availability slots exist (rolling refresh).

Alembic migration a3f2c1d4e5b6 seeds doctor_schedules once at upgrade time. After those
timestamps pass, get_available_slots returns nothing and voice inline booking says
"no available slots". We refresh future slots on each DB Agent startup, same idea as
seed_demo_patients_if_empty.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.engine import get_session_factory
from shared.db.models import DoctorSchedule
from shared.logging import get_logger

logger = get_logger("db_agent.seed_doctor_slots")

DOCTOR_ID = "doc-001"
DOCTOR_NAME = "Dr. Priya Patel"
# Medium-urgency availability uses a 7-day window; keep enough future rows across weekdays.
MIN_FUTURE_AVAILABLE_SLOTS = 12


def _gen_slot_tuples(now: datetime) -> list[tuple[datetime, datetime]]:
    """Mon–Fri 9:00–17:00 UTC, hourly slots for 3 weeks starting next Monday (matches migration)."""
    assert now.tzinfo is not None
    days_until_monday = (7 - now.weekday()) % 7 or 7
    start_date = (now + timedelta(days=days_until_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    out: list[tuple[datetime, datetime]] = []
    for week in range(3):
        for day in range(5):
            date = start_date + timedelta(weeks=week, days=day)
            for hour in range(9, 17):
                slot_start = date.replace(hour=hour, minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(hours=1)
                out.append((slot_start, slot_end))
    return out


def _normalize_ts(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


async def _ensure_doctor_schedule_slots(session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)

    # Drop expired availability rows (past slot_start, still marked available).
    await session.execute(
        delete(DoctorSchedule).where(
            DoctorSchedule.status == "available",
            DoctorSchedule.slot_start < now,
        )
    )

    horizon = now + timedelta(days=21)
    count_result = await session.execute(
        select(func.count())
        .select_from(DoctorSchedule)
        .where(
            DoctorSchedule.status == "available",
            DoctorSchedule.slot_start >= now,
            DoctorSchedule.slot_start <= horizon,
        )
    )
    future_available = int(count_result.scalar_one() or 0)
    if future_available >= MIN_FUTURE_AVAILABLE_SLOTS:
        logger.info("doctor_slots_ok", future_available=future_available)
        return

    existing = await session.execute(
        select(DoctorSchedule.slot_start).where(DoctorSchedule.doctor_id == DOCTOR_ID)
    )
    existing_starts = {_normalize_ts(t) for t in existing.scalars().all()}

    created = 0
    created_at = now
    for slot_start, slot_end in _gen_slot_tuples(now):
        if slot_start < now:
            continue
        ss = _normalize_ts(slot_start)
        se = _normalize_ts(slot_end)
        if ss in existing_starts:
            continue
        session.add(
            DoctorSchedule(
                id=str(uuid.uuid4()),
                doctor_id=DOCTOR_ID,
                doctor_name=DOCTOR_NAME,
                slot_start=ss,
                slot_end=se,
                status="available",
                patient_id=None,
                created_at=created_at,
            )
        )
        existing_starts.add(ss)
        created += 1

    logger.info(
        "doctor_slots_refreshed",
        created=created,
        future_available_before=future_available,
    )


async def ensure_doctor_schedule_slots_if_needed() -> None:
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            await _ensure_doctor_schedule_slots(session)

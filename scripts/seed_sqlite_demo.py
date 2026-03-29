#!/usr/bin/env python3
"""Manually seed the SQLite DB with demo patients (same data as DB Agent startup seed).

Usage (from repo root, with local venv/uv):

  DATABASE_URL=sqlite+aiosqlite:///./carebridge.db uv run python scripts/seed_sqlite_demo.py

Inside Docker the DB Agent runs this automatically unless SKIP_DEMO_SEED=1.
"""

from __future__ import annotations

import asyncio
import os
import sys


async def _run() -> None:
    if not os.getenv("DATABASE_URL", "").strip():
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./carebridge.db"

    from shared.db.engine import create_all_tables, init_db
    from services.db_agent.seed_demo import seed_demo_patients_if_empty

    await init_db()
    await create_all_tables()
    await seed_demo_patients_if_empty()
    print("Demo seed finished (skipped if rows already exist).", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(_run())

"""Insert demo patients into SQLite when the DB Agent starts (idempotent)."""

from __future__ import annotations

import json
import os
import uuid

from sqlalchemy import select

from shared.db.engine import get_session_factory
from shared.db.models import Appointment, DischargeSummary, Medication, Patient, Questionnaire
from shared.demo_seed_data import DEMO_PATIENT_SEEDS
from shared.logging import get_logger

logger = get_logger("db_agent.seed_demo")


def _id() -> str:
    return str(uuid.uuid4())


async def seed_demo_patients_if_empty() -> None:
    if os.getenv("SKIP_DEMO_SEED", "").strip().lower() in ("1", "true", "yes"):
        logger.info("demo_seed_skipped", reason="SKIP_DEMO_SEED")
        return

    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            result = await session.execute(select(Patient.id).where(Patient.id == DEMO_PATIENT_SEEDS[0]["id"]))
            if result.scalar_one_or_none() is not None:
                logger.info("demo_seed_skipped", reason="already_present")
                return

            for spec in DEMO_PATIENT_SEEDS:
                patient = Patient(
                    id=spec["id"],
                    name=spec["name"],
                    dob=spec.get("dob"),
                    phone=spec["phone"],
                    email=spec.get("email"),
                    status=spec["status"],
                    risk_level=spec.get("risk_level"),
                )
                session.add(patient)

                ds = spec["discharge_summary"]
                session.add(
                    DischargeSummary(
                        id=_id(),
                        patient_id=spec["id"],
                        diagnosis=ds["diagnosis"],
                        procedures=ds.get("procedures"),
                        discharge_date=ds.get("discharge_date"),
                        instructions=ds.get("instructions"),
                        raw_text=ds.get("raw_text", ""),
                    )
                )

                for med in spec.get("medications", []):
                    session.add(
                        Medication(
                            id=_id(),
                            patient_id=spec["id"],
                            name=med["name"],
                            dosage=med["dosage"],
                            frequency=med["frequency"],
                        )
                    )

                qspec = spec.get("questionnaire")
                if qspec:
                    session.add(
                        Questionnaire(
                            id=_id(),
                            patient_id=spec["id"],
                            questions_json=json.dumps(qspec["questions"]),
                            diagnosis_context=qspec.get("diagnosis_context", ""),
                        )
                    )

                for ap in spec.get("appointments", []):
                    session.add(
                        Appointment(
                            id=_id(),
                            patient_id=spec["id"],
                            appointment_type=ap["appointment_type"],
                            scheduled_at=ap.get("scheduled_at"),
                            status=ap.get("status", "scheduled"),
                            notes=ap.get("notes"),
                        )
                    )

            logger.info("demo_seed_complete", patients=len(DEMO_PATIENT_SEEDS))

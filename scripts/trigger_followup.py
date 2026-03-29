"""Manually trigger a follow-up voice call for a specific patient."""
from __future__ import annotations

import asyncio
import sys

import httpx

from shared.service_urls import db_agent_url, scheduler_url

SCHEDULER_URL = scheduler_url()
DB_AGENT_URL = db_agent_url()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/trigger_followup.py <patient_id>")
        print("\nTo find patient IDs, run:")
        print(f"  curl {DB_AGENT_URL}/patients")
        sys.exit(1)

    patient_id = sys.argv[1]

    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Looking up patient {patient_id}...")
        resp = await client.get(f"{DB_AGENT_URL}/patients/{patient_id}")
        if resp.status_code != 200:
            print(f"Patient not found: {resp.status_code}")
            sys.exit(1)

        patient = resp.json()
        print(f"Patient: {patient['name']} ({patient['phone']})")
        print(f"Risk:    {patient.get('risk_level', 'unknown')}")

        print(f"\nTriggering AI voice follow-up call...")
        resp = await client.post(f"{SCHEDULER_URL}/trigger/{patient_id}")
        if resp.status_code == 200:
            print(f"[OK] {resp.json()}")
            print(f"\nOutbound call initiated to {patient['phone']}.")
            print("Twilio will call the patient. Claude will ask the disease-specific questions.")
            print("Spoken responses will be interpreted by Claude and stored in the DB.")
        else:
            print(f"[ERROR] {resp.status_code}: {resp.text}")


if __name__ == "__main__":
    asyncio.run(main())

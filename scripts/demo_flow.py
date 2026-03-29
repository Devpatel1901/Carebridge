"""End-to-end demo: ingest discharge, trigger follow-up via real Twilio voice."""
from __future__ import annotations

import asyncio
import sys

import httpx

from shared.service_urls import (
    brain_agent_url,
    comm_agent_url,
    db_agent_url,
    frontend_url,
    scheduler_url,
)

BRAIN_AGENT_URL = brain_agent_url()
COMM_AGENT_URL = comm_agent_url()
DB_AGENT_URL = db_agent_url()
SCHEDULER_URL = scheduler_url()
FRONTEND_BASE = frontend_url()


async def wait_for_services():
    """Ensure all services are up."""
    services = {
        "Brain Agent": f"{BRAIN_AGENT_URL}/health",
        "Communication Agent (Twilio voice)": f"{COMM_AGENT_URL}/health",
        "DB Agent": f"{DB_AGENT_URL}/health",
        "Scheduler": f"{SCHEDULER_URL}/health",
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services.items():
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    print(f"  [OK] {name}")
                else:
                    print(f"  [WARN] {name} returned {resp.status_code}")
            except Exception:
                print(f"  [FAIL] {name} not reachable at {url}")
                return False
    return True


async def main():
    print("=" * 60)
    print("CareBridge - Full Demo Flow")
    print("=" * 60)

    print("\n[Step 0] Checking services...")
    if not await wait_for_services():
        print("\nPlease start all services first. Exiting.")
        sys.exit(1)

    print("\n[Step 1] Ingesting discharge summary...")
    from scripts.seed_data import DISCHARGE_SUMMARY

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BRAIN_AGENT_URL}/intake",
            json={
                "patient_name": "Neel Sachhin Shah",
                "patient_phone": "+19302159133",
                "patient_dob": "1959-03-15",
                "patient_email": "shahneel190@gmail.com",
                "discharge_summary_text": DISCHARGE_SUMMARY,
            },
        )

        if response.status_code != 200:
            print(f"  [ERROR] Intake failed: {response.status_code} {response.text}")
            sys.exit(1)

        intake_data = response.json()
        patient_id = intake_data["patient_id"]
        print(f"  [OK] Patient: {patient_id}")
        print(f"       Risk: {intake_data['risk_level']}")
        print(f"       Decision: {intake_data['decision']}")
        print(f"       Questions generated: {len(intake_data.get('generated_questions', []))}")

    print("\n[Step 2] Waiting for event propagation (5s)...")
    await asyncio.sleep(5)

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n[Step 3] Checking patient in DB...")
        resp = await client.get(f"{DB_AGENT_URL}/patients/{patient_id}")
        if resp.status_code == 200:
            patient = resp.json()
            print(f"  [OK] Patient found: {patient['name']}")
            print(f"       Status: {patient['status']}")
            print(f"       Risk: {patient['risk_level']}")
            if patient.get("discharge_summary"):
                print(f"       Diagnosis: {patient['discharge_summary']['diagnosis']}")
            if patient.get("medications"):
                print(f"       Medications: {len(patient['medications'])}")
            if patient.get("questionnaire"):
                qs = patient["questionnaire"].get("questions", [])
                print(f"       Questionnaire: {len(qs)} questions")
        else:
            print(f"  [WARN] Patient not found yet: {resp.status_code}")

        print("\n[Step 4] Checking scheduled jobs...")
        resp = await client.get(f"{SCHEDULER_URL}/jobs")
        if resp.status_code == 200:
            jobs = resp.json()
            print(f"  [OK] {len(jobs)} jobs scheduled")
            for job in jobs:
                print(f"       - {job['name']} @ {job['next_run_time']}")
        else:
            print(f"  [WARN] Could not fetch jobs: {resp.status_code}")

        print("\n[Step 5] Manually triggering AI voice follow-up call...")
        resp = await client.post(f"{SCHEDULER_URL}/trigger/{patient_id}")
        if resp.status_code == 200:
            body = resp.json()
            print(f"  [OK] Follow-up triggered: {body}")
            call = body.get("call") or {}
            if call.get("voice_session_id"):
                print(f"       voice_session_id: {call['voice_session_id']}")
            if call.get("call_sid"):
                print(f"       Twilio call_sid: {call['call_sid']}")
            print("  Twilio is calling the patient's phone number now.")
            print("  Ensure ngrok points to :8002 and TWILIO_WEBHOOK_BASE_URL matches your ngrok HTTPS URL.")
            print("  Claude interprets spoken answers; check Communication Agent logs if the call errors.")
        else:
            print(f"  [ERROR] Trigger failed: {resp.status_code} {resp.text}")

    print("\n" + "=" * 60)
    print("Demo flow complete!")
    print(f"\nDashboard: {FRONTEND_BASE}")
    print(f"Patient:   {FRONTEND_BASE}/patients/{patient_id}")
    print(f"Alerts:    {FRONTEND_BASE}/alerts")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

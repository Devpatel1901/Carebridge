"""
Demo patient records for SQLite seeding — single source of truth for IDs, names, phones, and clinical rows.

The Next.js home table loads from `GET /patients` (DB Agent), so ward list IDs and labels match this data
after seed. Use `existing_patient_id` on Brain `/intake` to update these rows in place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_APPT_BASE = datetime(2026, 4, 5, 14, 30, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Five demo patients — diagnosis aligned with ward “Reason” column
# ---------------------------------------------------------------------------

DEMO_PATIENT_SEEDS: list[dict[str, Any]] = [
    {
        "id": "1024587",
        "name": "Neel Sachin Shah",
        "dob": "1983-06-12",
        "phone": "+19302159133",
        "email": "neelshah190@gmail.com",
        "status": "Stable",
        "risk_level": "high",
        "discharge_summary": {
            "diagnosis": "Traumatic brain injury (concussion) with brief LOC — monitoring in ICU",
            "procedures": "CT head without contrast; neuro checks q2h; ICP monitoring per protocol.",
            "discharge_date": "2026-03-27",
            "instructions": "Neuro follow-up in 1 week; avoid contact sports; return for worsening headache, vomiting, or confusion.",
            "raw_text": """DISCHARGE SUMMARY
Patient: Neel Sachin Shah
DOB: 1983-06-12
Phone: +19302159133

Admission: 2026-03-22  Discharge: 2026-03-27
Primary diagnosis: Traumatic brain injury (concussion) with brief loss of consciousness

Hospital course: Patient struck head during fall; GCS 14 on arrival. Imaging negative for acute bleed.
Neurology consulted; symptoms improved with rest and medication optimization.

Discharge medications:
- Acetaminophen 650 mg PO q6h PRN pain
- Ondansetron 4 mg PO q8h PRN nausea

Follow-up: Neurosurgery clinic in 7 days; return to ED for red flags.
""",
        },
        "medications": [
            {"name": "Acetaminophen", "dosage": "650 mg", "frequency": "q6h PRN"},
            {"name": "Ondansetron", "dosage": "4 mg", "frequency": "q8h PRN"},
        ],
        "questionnaire": {
            "diagnosis_context": "Post-concussion follow-up",
            "questions": [
                {
                    "id": "q1",
                    "text": "Have you had any new or worsening headaches since discharge?",
                    "question_type": "yes_no",
                    "relevance": "high",
                },
                {
                    "id": "q2",
                    "text": "Any nausea, vomiting, or vision changes?",
                    "question_type": "yes_no",
                    "relevance": "high",
                },
            ],
        },
        "appointments": [
            {
                "appointment_type": "Neurosurgery follow-up",
                "scheduled_at": _APPT_BASE,
                "status": "scheduled",
                "notes": "Bring medication list; ICU-3 discharge.",
            }
        ],
    },
    {
        "id": "7658321",
        "name": "Abhishek Sutaria",
        "dob": "1985-11-03",
        "phone": "+19303337194",
        "email": "abhishek.sutaria@gmail.com",
        "status": "Discharged",
        "risk_level": "low",
        "discharge_summary": {
            "diagnosis": "Heart failure with reduced ejection fraction (HFrEF) — compensated",
            "procedures": "Echocardiogram; diuresis; medication optimization.",
            "discharge_date": "2026-03-25",
            "instructions": "Low-sodium diet; daily weights; cardiology in 2 weeks.",
            "raw_text": """DISCHARGE SUMMARY
Patient: Abhishek Sutaria
Phone: +19303337194

Primary diagnosis: Heart failure with reduced ejection fraction

Hospital course: Volume overload treated with IV diuresis; EF 35% on echo. Patient educated on fluid restriction.

Discharge medications:
- Furosemide 40 mg daily
- Carvedilol 12.5 mg BID
- Lisinopril 10 mg daily

Follow-up: Cardiology outpatient.
""",
        },
        "medications": [
            {"name": "Furosemide", "dosage": "40 mg", "frequency": "daily"},
            {"name": "Carvedilol", "dosage": "12.5 mg", "frequency": "BID"},
            {"name": "Lisinopril", "dosage": "10 mg", "frequency": "daily"},
        ],
        "questionnaire": {
            "diagnosis_context": "Heart failure symptom check-in",
            "questions": [
                {
                    "id": "q1",
                    "text": "Any increased shortness of breath or swelling in your legs?",
                    "question_type": "yes_no",
                    "relevance": "high",
                },
                {
                    "id": "q2",
                    "text": "Are you taking all prescribed medications as directed?",
                    "question_type": "yes_no",
                    "relevance": "medium",
                },
            ],
        },
        "appointments": [
            {
                "appointment_type": "Cardiology",
                "scheduled_at": _APPT_BASE.replace(day=8),
                "status": "scheduled",
                "notes": "Post-discharge — ward R-18.",
            }
        ],
    },
    {
        "id": "2156793",
        "name": "Dev Patel",
        "dob": "1959-01-20",
        "phone": "+18128780868",
        "email": "entrepreneurdev1901@gmail.com",
        "status": "Recovering",
        "risk_level": "medium",
        "discharge_summary": {
            "diagnosis": "Community-acquired pneumonia (CAP) — clinical improvement on antibiotics",
            "procedures": "Supplemental oxygen wean; IV to oral antibiotic transition.",
            "discharge_date": "2026-03-28",
            "instructions": "Complete antibiotic course; pulmonary follow-up; return if fever or worsening breathing.",
            "raw_text": """DISCHARGE SUMMARY
Patient: Dev Patel
DOB: 1959-01-20
Phone: +18128780868
Email: entrepreneurdev1901@gmail.com

Admission: 2026-03-20  Discharge: 2026-03-28
Primary diagnosis: Community-acquired pneumonia (CAP)

Hospital course: Patient admitted with fever, productive cough, and hypoxia. Treated with ceftriaxone and azithromycin with good response. Oxygen weaned to room air.

Discharge medications:
- Amoxicillin-clavulanate 875/125 mg BID to complete 7-day course
- Albuterol inhaler 2 puffs q4-6h PRN wheeze

Follow-up: Primary care in 1 week; pulmonology if symptoms persist.
Attending: Dr. Ahmed Khan
""",
        },
        "medications": [
            {
                "name": "Amoxicillin-clavulanate",
                "dosage": "875/125 mg",
                "frequency": "BID",
            },
            {"name": "Albuterol", "dosage": "90 mcg", "frequency": "q4-6h PRN"},
        ],
        "questionnaire": {
            "diagnosis_context": "Post-pneumonia recovery",
            "questions": [
                {
                    "id": "q1",
                    "text": "Are you still having cough or fever?",
                    "question_type": "yes_no",
                    "relevance": "high",
                },
                {
                    "id": "q2",
                    "text": "Can you complete daily activities without getting winded?",
                    "question_type": "yes_no",
                    "relevance": "medium",
                },
            ],
        },
        "appointments": [
            {
                "appointment_type": "Primary care follow-up",
                "scheduled_at": _APPT_BASE.replace(day=12),
                "status": "scheduled",
                "notes": "G-12 / Bed A",
            }
        ],
    },
    {
        "id": "3298461",
        "name": "Ananya Vasisht",
        "dob": "1939-04-08",
        "phone": "+19309044337",
        "email": None,
        "status": "Stable",
        "risk_level": "low",
        "discharge_summary": {
            "diagnosis": "Post-operative recovery after elective procedure — stable",
            "procedures": "Wound care; PT evaluation; pain control.",
            "discharge_date": "2026-03-26",
            "instructions": "Wound checks; DVT prophylaxis per protocol; PT home exercises.",
            "raw_text": """DISCHARGE SUMMARY
Patient: Ananya Vasisht
Phone: +19309044337

Primary diagnosis: Post-operative recovery — stable

Hospital course: Recovering well from procedure; ambulating with assistance; pain controlled with oral analgesics.

Discharge medications:
- Acetaminophen 650 mg q6h PRN
- Enoxaparin 40 mg SQ daily (per protocol)

Follow-up: Surgical clinic; physical therapy as arranged.
""",
        },
        "medications": [
            {"name": "Acetaminophen", "dosage": "650 mg", "frequency": "q6h PRN"},
            {"name": "Enoxaparin", "dosage": "40 mg", "frequency": "daily SQ"},
        ],
        "questionnaire": {
            "diagnosis_context": "Post-operative wellness",
            "questions": [
                {
                    "id": "q1",
                    "text": "Any increased pain or redness at the surgical site?",
                    "question_type": "yes_no",
                    "relevance": "high",
                },
            ],
        },
        "appointments": [
            {
                "appointment_type": "Surgical follow-up",
                "scheduled_at": _APPT_BASE.replace(day=15),
                "status": "scheduled",
                "notes": "Ward R-14",
            }
        ],
    },
    {
        "id": "4532109",
        "name": "Habib Chowdhury",
        "dob": "1998-02-14",
        "phone": "+15554532109",
        "email": None,
        "status": "Stable",
        "risk_level": "low",
        "discharge_summary": {
            "diagnosis": "Post-operative recovery — monitored in ICU step-down",
            "procedures": "Continuous monitoring; IV fluids titrated; early mobilization when safe.",
            "discharge_date": "2026-03-29",
            "instructions": "Gradual activity increase; wound care instructions provided; return for fever or drainage.",
            "raw_text": """DISCHARGE SUMMARY
Patient: Habib Chowdhury
Phone: +15554532109

Primary diagnosis: Post-operative recovery

Hospital course: Patient stable for transfer from ICU-9; vitals trending normal; tolerating diet.

Discharge medications:
- Ibuprofen 400 mg q8h PRN pain
- Omeprazole 20 mg daily

Follow-up: Surgery/primary care as scheduled.
""",
        },
        "medications": [
            {"name": "Ibuprofen", "dosage": "400 mg", "frequency": "q8h PRN"},
            {"name": "Omeprazole", "dosage": "20 mg", "frequency": "daily"},
        ],
        "questionnaire": {
            "diagnosis_context": "Post-operative check-in",
            "questions": [
                {
                    "id": "q1",
                    "text": "Any fever, chills, or wound drainage?",
                    "question_type": "yes_no",
                    "relevance": "high",
                },
            ],
        },
        "appointments": [
            {
                "appointment_type": "Clinic follow-up",
                "scheduled_at": _APPT_BASE.replace(day=18),
                "status": "scheduled",
                "notes": "ICU-9",
            }
        ],
    },
]

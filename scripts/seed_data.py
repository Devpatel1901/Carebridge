"""Seed a realistic discharge summary into the Brain Agent."""
from __future__ import annotations

import asyncio
import sys

import httpx

from shared.service_urls import brain_agent_url

BRAIN_AGENT_URL = brain_agent_url()

DISCHARGE_SUMMARY = """
DISCHARGE SUMMARY

Patient: Abhishek Manoj Sutaria
Date of Birth: 1959-03-15
Phone: +19303337194
Email: shahneel190@gmail.com

Admission Date: 2026-03-20
Discharge Date: 2026-03-26

Primary Diagnosis: Acute ST-elevation myocardial infarction (STEMI) of the anterior wall

Procedures Performed:
- Emergency coronary angiography
- Percutaneous coronary intervention (PCI) with drug-eluting stent placement in the left anterior descending artery (LAD)

Hospital Course:
Patient presented to the ED with crushing substernal chest pain radiating to the left arm, diaphoresis, and nausea. ECG showed ST-elevation in leads V1-V4. Troponin I elevated at 15.2 ng/mL. Patient was taken emergently to the cath lab where a 95% occlusion of the proximal LAD was identified and treated with a drug-eluting stent. Post-procedure course was uncomplicated. Echocardiogram showed EF of 45% with anterior wall hypokinesis. Patient remained hemodynamically stable and was weaned off heparin drip on day 3.

Discharge Medications:
1. Aspirin 81 mg daily - antiplatelet, do not stop
2. Clopidogrel (Plavix) 75 mg daily - dual antiplatelet, take for at least 12 months
3. Metoprolol succinate 50 mg daily - beta-blocker for heart rate and BP control
4. Atorvastatin 80 mg at bedtime - high-intensity statin
5. Lisinopril 10 mg daily - ACE inhibitor for cardiac remodeling
6. Nitroglycerin 0.4 mg sublingual PRN - for chest pain, call 911 if no relief after 3 doses

Discharge Instructions:
- Follow up with cardiology in 2 weeks
- Monitor blood pressure daily; target < 130/80
- Cardiac rehabilitation referral - start in 2 weeks
- Strict low-sodium, heart-healthy diet
- No heavy lifting (> 10 lbs) for 6 weeks
- Call 911 immediately if experiencing chest pain, shortness of breath, or fainting
- Do not stop aspirin or clopidogrel without consulting your cardiologist
- Return to ED if experiencing excessive bruising, blood in stool, or severe headache

Attending Physician: Dr. Sarah Chen, MD, FACC
"""


async def main():
    print("=" * 60)
    print("CareBridge - Seeding discharge summary")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n[1] Sending discharge summary to Brain Agent...")

        response = await client.post(
            f"{BRAIN_AGENT_URL}/intake",
            json={
                "patient_name": "Neel Sachin Shah",
                "patient_phone": "+19303337194",
                "patient_dob": "1959-03-15",
                "patient_email": "shahneel190@gmail.com",
                "discharge_summary_text": DISCHARGE_SUMMARY,
            },
        )

        if response.status_code == 200:
            data = response.json()
            print(f"\n[OK] Patient created: {data['patient_id']}")
            print(f"     Risk level:  {data['risk_level']}")
            print(f"     Decision:    {data['decision']}")
            print(f"     Questions:   {len(data.get('generated_questions', []))}")
            print(f"     Correlation: {data['correlation_id']}")

            if data.get("generated_questions"):
                print("\n     Generated follow-up questions:")
                for q in data["generated_questions"]:
                    print(f"       - [{q.get('question_type', 'open')}] {q.get('text', '')}")

            print(f"\n[INFO] Patient ID: {data['patient_id']}")
            print("       Use this ID for follow-up triggers and dashboard queries.")
            return data["patient_id"]
        else:
            print(f"\n[ERROR] Status {response.status_code}: {response.text}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

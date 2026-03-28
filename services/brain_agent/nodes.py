from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage

from shared.events.contracts import (
    AlertType,
    DecisionType,
    JobType,
    RiskLevel,
    Severity,
)
from shared.logging import get_logger
from services.brain_agent.llm import get_llm

logger = get_logger("brain_agent.nodes")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class BrainState(TypedDict, total=False):
    raw_text: str
    patient_name: str
    patient_phone: str
    patient_dob: str | None
    patient_email: str | None
    patient_id: str
    parsed_summary: dict[str, Any]
    extracted_data: dict[str, Any]
    risk_evaluation: dict[str, Any]
    generated_questions: list[dict[str, Any]]
    patient_response: dict[str, Any]
    response_analysis: dict[str, Any]
    decision: dict[str, Any]
    actions: list[dict[str, Any]]
    correlation_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _llm_json_call(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Invoke the LLM and parse the response as JSON."""
    llm = get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n")
        text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()
    return json.loads(text)


_RISK_MAP = {
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}

_DECISION_MAP = {
    "stable": DecisionType.STABLE,
    "followup_needed": DecisionType.FOLLOWUP_NEEDED,
    "alert": DecisionType.ALERT,
    "escalation": DecisionType.ESCALATION,
    "appointment_required": DecisionType.APPOINTMENT_REQUIRED,
}


# ---------------------------------------------------------------------------
# Node 1 – Parse Discharge Summary
# ---------------------------------------------------------------------------

def parse_summary_node(state: BrainState) -> dict[str, Any]:
    """Use Claude to parse raw discharge text into structured data."""
    raw_text = state.get("raw_text", "")
    logger.info("parse_summary_node.start", patient_id=state.get("patient_id"))

    system_prompt = (
        "You are a clinical NLP system. Parse the following hospital discharge "
        "summary and extract structured information. Respond ONLY with valid JSON "
        "(no markdown fences, no commentary). Use this exact schema:\n"
        "{\n"
        '  "diagnosis": "<primary diagnosis>",\n'
        '  "procedures": "<procedures performed, or null>",\n'
        '  "medications": [{"name": "...", "dosage": "...", "frequency": "..."}],\n'
        '  "discharge_date": "<YYYY-MM-DD or null>",\n'
        '  "instructions": "<discharge instructions>",\n'
        '  "demographics": {"name": "<if found or null>", '
        '"dob": "<if found or null>", "phone": "<if found or null>", '
        '"email": "<if found or null>"}\n'
        "}"
    )

    try:
        parsed = _llm_json_call(system_prompt, raw_text)
    except Exception:
        logger.exception("parse_summary_node.llm_error")
        parsed = {
            "diagnosis": "Unable to parse",
            "procedures": None,
            "medications": [],
            "discharge_date": None,
            "instructions": raw_text[:500],
            "demographics": {},
        }

    return {"parsed_summary": parsed}


# ---------------------------------------------------------------------------
# Node 2 – Extract & Normalize Data
# ---------------------------------------------------------------------------

def extract_data_node(state: BrainState) -> dict[str, Any]:
    """Pure-Python transformation: merge parsed summary with top-level fields."""
    parsed = state.get("parsed_summary", {})
    llm_demo = parsed.get("demographics", {})

    demographics = {
        "name": state.get("patient_name") or llm_demo.get("name") or "Unknown",
        "phone": state.get("patient_phone") or llm_demo.get("phone") or "",
        "dob": state.get("patient_dob") or llm_demo.get("dob"),
        "email": state.get("patient_email") or llm_demo.get("email"),
    }

    discharge = {
        "diagnosis": parsed.get("diagnosis", "Unknown"),
        "procedures": parsed.get("procedures"),
        "discharge_date": parsed.get("discharge_date"),
        "instructions": parsed.get("instructions"),
        "raw_text": state.get("raw_text", ""),
    }

    medications = parsed.get("medications", [])
    for med in medications:
        med.setdefault("name", "Unknown")
        med.setdefault("dosage", "Unknown")
        med.setdefault("frequency", "Unknown")

    extracted = {
        "demographics": demographics,
        "discharge": discharge,
        "medications": medications,
    }

    return {"extracted_data": extracted}


# ---------------------------------------------------------------------------
# Node 3 – Risk Evaluation
# ---------------------------------------------------------------------------

def risk_evaluation_node(state: BrainState) -> dict[str, Any]:
    """Use Claude to assess patient risk level."""
    extracted = state.get("extracted_data", {})
    discharge = extracted.get("discharge", {})
    medications = extracted.get("medications", [])

    logger.info("risk_evaluation_node.start", patient_id=state.get("patient_id"))

    system_prompt = (
        "You are a clinical risk-assessment engine. Given a patient's diagnosis, "
        "procedures, and medications, evaluate the post-discharge risk. "
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "risk_level": "low|medium|high|critical",\n'
        '  "reasoning": "<brief explanation>",\n'
        '  "risk_factors": ["factor1", "factor2"]\n'
        "}"
    )

    user_prompt = (
        f"Diagnosis: {discharge.get('diagnosis', 'N/A')}\n"
        f"Procedures: {discharge.get('procedures', 'N/A')}\n"
        f"Medications: {json.dumps(medications)}\n"
        f"Instructions: {discharge.get('instructions', 'N/A')}"
    )

    try:
        result = _llm_json_call(system_prompt, user_prompt)
        result.setdefault("risk_level", "medium")
        result.setdefault("reasoning", "")
        result.setdefault("risk_factors", [])
    except Exception:
        logger.exception("risk_evaluation_node.llm_error")
        result = {
            "risk_level": "medium",
            "reasoning": "Unable to evaluate risk; defaulting to medium.",
            "risk_factors": [],
        }

    return {"risk_evaluation": result}


# ---------------------------------------------------------------------------
# Node 4 – Questionnaire Generation
# ---------------------------------------------------------------------------

def questionnaire_generation_node(state: BrainState) -> dict[str, Any]:
    """Use Claude to generate disease-specific follow-up questions."""
    extracted = state.get("extracted_data", {})
    discharge = extracted.get("discharge", {})
    medications = extracted.get("medications", [])
    risk_eval = state.get("risk_evaluation", {})

    logger.info(
        "questionnaire_generation_node.start",
        patient_id=state.get("patient_id"),
    )

    system_prompt = (
        "You are a clinical follow-up question generator. Based on the patient's "
        "diagnosis, procedures, and medications, generate EXACTLY 2 highly specific "
        "follow-up questions that a nurse should ask during a post-discharge "
        "check-in. Each question must be tailored to THIS patient's condition. "
        "Prioritise the highest-risk symptoms first.\n\n"
        "Respond ONLY with a JSON array of exactly 2 elements (no wrapping object). Each element:\n"
        "{\n"
        '  "id": "q1",\n'
        '  "text": "<the question>",\n'
        '  "question_type": "open|yes_no|scale",\n'
        '  "relevance": "<why this question matters for this patient>"\n'
        "}\n\n"
        "Examples of specificity:\n"
        '- Cardiac: "Have you experienced any chest tightness or shortness of '
        'breath since discharge?"\n'
        '- Post-surgical: "Is there any redness, swelling, or drainage at the '
        'incision site?"\n'
        '- Diabetes: "Have you been able to check your blood sugar levels '
        'regularly?"'
    )

    user_prompt = (
        f"Diagnosis: {discharge.get('diagnosis', 'N/A')}\n"
        f"Procedures: {discharge.get('procedures', 'N/A')}\n"
        f"Medications: {json.dumps(medications)}\n"
        f"Risk level: {risk_eval.get('risk_level', 'N/A')}\n"
        f"Risk factors: {json.dumps(risk_eval.get('risk_factors', []))}"
    )

    try:
        raw = _llm_json_call(system_prompt, user_prompt)
        if isinstance(raw, dict) and "questions" in raw:
            questions = raw["questions"]
        elif isinstance(raw, list):
            questions = raw
        else:
            questions = [raw]

        for i, q in enumerate(questions):
            q.setdefault("id", f"q{i + 1}")
            q.setdefault("text", "")
            q.setdefault("question_type", "open")
            q.setdefault("relevance", "")
    except Exception:
        logger.exception("questionnaire_generation_node.llm_error")
        questions = [
            {
                "id": "q1",
                "text": "How are you feeling since your discharge?",
                "question_type": "open",
                "relevance": "General wellness check",
            }
        ]

    return {"generated_questions": questions}


# ---------------------------------------------------------------------------
# Node 5 – Response Analysis (response flow)
# ---------------------------------------------------------------------------

def response_analysis_node(state: BrainState) -> dict[str, Any]:
    """Analyze patient responses for clinical significance."""
    patient_response = state.get("patient_response", {})
    responses = patient_response.get("responses", [])
    diagnosis_context = patient_response.get("diagnosis", "Unknown")

    logger.info(
        "response_analysis_node.start",
        patient_id=state.get("patient_id"),
        response_count=len(responses),
    )

    system_prompt = (
        "You are a clinical response-analysis engine. A patient has answered "
        "post-discharge follow-up questions. Analyze each response for clinical "
        "significance given the patient's diagnosis.\n\n"
        "MANDATORY CLINICAL RULES — these override all other reasoning:\n"
        "- chest pain / pressure / nitroglycerin use in ANY cardiac patient = 'high'\n"
        "- shortness of breath / dyspnea in post-cardiac patient = 'high'\n"
        "- missed cardiac medications (aspirin, clopidogrel, beta-blockers) = 'high'\n"
        "- fever > 38C / signs of infection post-surgery = 'high'\n"
        "- bleeding on anticoagulants (blood in stool, urine, unusual bruising) = 'high'\n"
        "- new leg/ankle swelling post-cardiac = 'medium'\n"
        "- reduced energy/fatigue scale ≤ 5 = 'medium'\n"
        "- all clear / no symptoms = 'low'\n\n"
        "Also check the 'clinical_flags' field per response — these are pre-flagged "
        "symptoms already detected during the call. If clinical_flags is non-empty, "
        "the concern_level must be at least 'medium'.\n\n"
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "analysis": [\n'
        "    {\n"
        '      "question_id": "...",\n'
        '      "concern_level": "low|medium|high",\n'
        '      "interpretation": "one concise sentence"\n'
        "    }\n"
        "  ],\n"
        '  "overall_concern": "low|medium|high",\n'
        '  "flags": ["specific symptom detected, e.g. chest_pain, shortness_of_breath"]\n'
        "}"
    )

    formatted_responses = "\n".join(
        f"Q ({r.get('question_id', '?')}): {r.get('question_text', '?')}\n"
        f"A: {r.get('answer', 'N/A')} | normalized: {r.get('normalized', 'N/A')}"
        f" | clinical_flags: {r.get('clinical_flags', [])}"
        for r in responses
    )

    user_prompt = (
        f"Patient diagnosis: {diagnosis_context}\n\n"
        f"Responses:\n{formatted_responses}"
    )

    try:
        result = _llm_json_call(system_prompt, user_prompt)
        result.setdefault("analysis", [])
        result.setdefault("overall_concern", "low")
        result.setdefault("flags", [])
    except Exception:
        logger.exception("response_analysis_node.llm_error")
        result = {
            "analysis": [],
            "overall_concern": "medium",
            "flags": ["automated_analysis_failed"],
        }

    return {"response_analysis": result}


# ---------------------------------------------------------------------------
# Node 6 – Decision
# ---------------------------------------------------------------------------

def decision_node(state: BrainState) -> dict[str, Any]:
    """Use Claude to decide the clinical course of action."""
    risk_eval = state.get("risk_evaluation", {})
    response_analysis = state.get("response_analysis")

    logger.info("decision_node.start", patient_id=state.get("patient_id"))

    system_prompt = (
        "You are a clinical decision engine. Based on the risk evaluation and "
        "(if available) the response analysis, decide the next action.\n\n"
        "Decision types:\n"
        "- stable: Patient is doing well, continue normal follow-up.\n"
        "- followup_needed: Schedule an additional follow-up sooner.\n"
        "- alert: Create a clinical alert for the care team.\n"
        "- escalation: Urgent escalation to a provider.\n"
        "- appointment_required: Schedule an in-person appointment.\n\n"
        "Respond ONLY with valid JSON:\n"
        "{\n"
        '  "decision_type": "stable|followup_needed|alert|escalation|appointment_required",\n'
        '  "reasoning": "...",\n'
        '  "urgency": "low|medium|high|critical"\n'
        "}"
    )

    context_parts = [f"Risk level: {risk_eval.get('risk_level', 'N/A')}"]
    context_parts.append(f"Risk reasoning: {risk_eval.get('reasoning', 'N/A')}")
    context_parts.append(
        f"Risk factors: {json.dumps(risk_eval.get('risk_factors', []))}"
    )

    if response_analysis:
        context_parts.append(
            f"Overall concern from responses: "
            f"{response_analysis.get('overall_concern', 'N/A')}"
        )
        context_parts.append(
            f"Flags: {json.dumps(response_analysis.get('flags', []))}"
        )
        context_parts.append(
            f"Response analysis: {json.dumps(response_analysis.get('analysis', []))}"
        )

    user_prompt = "\n".join(context_parts)

    try:
        result = _llm_json_call(system_prompt, user_prompt)
        result.setdefault("decision_type", "stable")
        result.setdefault("reasoning", "")
        result.setdefault("urgency", "low")
    except Exception:
        logger.exception("decision_node.llm_error")
        result = {
            "decision_type": "followup_needed",
            "reasoning": "Unable to determine; defaulting to follow-up.",
            "urgency": "medium",
        }

    return {"decision": result}


# ---------------------------------------------------------------------------
# Node 7 – Action Generation
# ---------------------------------------------------------------------------

_SEVERITY_MAP = {
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}


def _followup_delay(urgency: str) -> timedelta:
    return {
        "low": timedelta(days=3),
        "medium": timedelta(days=1),
        "high": timedelta(hours=6),
        "critical": timedelta(hours=1),
    }.get(urgency, timedelta(days=1))


def action_generation_node(state: BrainState) -> dict[str, Any]:
    """Pure-Python node that converts the decision into publishable event actions."""
    decision = state.get("decision", {})
    decision_type = decision.get("decision_type", "stable")
    urgency = decision.get("urgency", "low")
    reasoning = decision.get("reasoning", "")
    patient_id = state.get("patient_id", str(uuid.uuid4()))
    correlation_id = state.get("correlation_id", str(uuid.uuid4()))

    extracted = state.get("extracted_data", {})
    demographics = extracted.get("demographics", {})
    discharge = extracted.get("discharge", {})
    medications = extracted.get("medications", [])
    risk_eval = state.get("risk_evaluation", {})
    questions = state.get("generated_questions", [])

    # True when this node runs after a voice response (not intake)
    is_response_chain = state.get("patient_response") is not None

    actions: list[dict[str, Any]] = []

    # Only emit PatientStateUpsert from intake chain (has real extracted data).
    # Skipping during response chain prevents overwriting the DB with empty fields.
    if not is_response_chain:
        risk_str = risk_eval.get("risk_level", "low")
        actions.append({
            "type": "patient_state_upsert",
            "patient_id": patient_id,
            "correlation_id": correlation_id,
            "demographics": demographics,
            "discharge_data": discharge,
            "medications": medications,
            "risk_level": risk_str,
            "generated_questions": questions,
        })

    # Alert / Escalation
    if decision_type in ("alert", "escalation"):
        sev = _SEVERITY_MAP.get(urgency, Severity.MEDIUM)
        response_analysis = state.get("response_analysis", {})
        analysis_items = response_analysis.get("analysis", [])
        flags = response_analysis.get("flags", [])

        # Build per-question concern lookup from the raw responses
        patient_response = state.get("patient_response", {})
        raw_responses = patient_response.get("responses", [])
        resp_by_qid = {r.get("question_id", ""): r for r in raw_responses}

        # One bullet per medium/high concern question
        concern_lines: list[str] = []
        for item in analysis_items:
            level = item.get("concern_level", "low")
            if level not in ("medium", "high"):
                continue
            qid = item.get("question_id", "")
            resp = resp_by_qid.get(qid, {})
            q_text = resp.get("question_text") or qid
            answer = resp.get("answer") or resp.get("normalized") or "—"
            interp = item.get("interpretation", "").strip()
            flags_for_q = resp.get("clinical_flags", [])
            flag_str = f"  Flags: {', '.join(flags_for_q)}" if flags_for_q else ""
            concern_lines.append(
                f"[{level.upper()}]  {q_text}\n"
                f"  Patient said: \"{answer}\"\n"
                f"  Assessment: {interp}{flag_str}"
            )

        # Fallback: if no per-question lines, list raw flags
        if not concern_lines:
            concern_lines = [f"[MEDIUM]  {f}" for f in flags] if flags else ["[MEDIUM]  Clinical concern detected"]

        alert_msg = "\n\n".join(concern_lines)
        actions.append({
            "type": "alert_event",
            "patient_id": patient_id,
            "correlation_id": correlation_id,
            "alert_type": AlertType.GENERAL.value,
            "severity": sev.value,
            "message": alert_msg,
        })

    # Appointment
    if decision_type == "appointment_required":
        actions.append({
            "type": "schedule_event",
            "patient_id": patient_id,
            "correlation_id": correlation_id,
            "job_type": JobType.APPOINTMENT.value,
            "scheduled_at": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
            "metadata": {"reason": reasoning},
        })

    # Schedule next follow-up; tag response-chain events so demo mode uses real delay
    delay = _followup_delay(urgency)
    actions.append({
        "type": "schedule_event",
        "patient_id": patient_id,
        "correlation_id": correlation_id,
        "job_type": JobType.FOLLOWUP.value,
        "scheduled_at": (datetime.now(timezone.utc) + delay).isoformat(),
        "metadata": {
            "decision_type": decision_type,
            "urgency": urgency,
            "from_response_chain": is_response_chain,
        },
    })

    logger.info(
        "action_generation_node.done",
        patient_id=patient_id,
        action_count=len(actions),
    )

    return {"actions": actions}

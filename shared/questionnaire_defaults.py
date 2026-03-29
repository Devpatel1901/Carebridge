"""Shared questionnaire fragments used by Brain intake and DB Agent read paths."""

from __future__ import annotations

from typing import Any

APPOINTMENT_CONSENT_QUESTION: dict[str, Any] = {
    "id": "q_appt_consent",
    "text": (
        "Based on how you're feeling, would you like to schedule an "
        "in-person appointment with your doctor?"
    ),
    "question_type": "appointment_consent",
    "relevance": "Patient consent for appointment scheduling",
}


def ensure_appointment_consent_question(questions: Any) -> tuple[list[Any], bool]:
    """
    If `questions` is a list missing q_appt_consent, append a copy of
    APPOINTMENT_CONSENT_QUESTION.

    Returns (normalized_list, injected) where injected is True when a row was added.
    Non-list input yields ([], False).
    """
    if not isinstance(questions, list):
        return [], False
    if any(
        isinstance(q, dict) and q.get("id") == "q_appt_consent"
        for q in questions
    ):
        return questions, False
    return [*questions, {**APPOINTMENT_CONSENT_QUESTION}], True

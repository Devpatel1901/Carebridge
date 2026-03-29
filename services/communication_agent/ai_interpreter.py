"""Claude-powered speech interpretation for voice call responses."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from shared.config import get_settings
from shared.logging import get_logger

logger = get_logger("ai_interpreter")

# Twilio waits ~15s for voice webhooks; LLM + Redis + TwiML must stay under that.
# HTTP client timeout is slightly lower than asyncio.wait_for so the SDK fails first.
LLM_TIMEOUT_SEC = 11.0
ANTHROPIC_HTTP_TIMEOUT_SEC = 10.0


class InterpretedResponse(BaseModel):
    raw_speech: str
    interpreted_answer: str
    normalized: str
    clinical_flags: list[str]
    needs_clarification: bool
    clarification_question: str | None = None


_SYSTEM_PROMPT = """\
You are a clinical AI assistant interpreting a patient's spoken response \
during a post-discharge follow-up phone call.

Your job is to:
1. Understand what the patient actually said in the context of the question asked.
2. Produce a clear, concise clinical summary of their answer.
3. For yes/no questions: extract a definitive "yes" or "no" normalized value even \
from natural speech (e.g. "yeah I guess", "not really", "kind of").
4. Identify any clinical red flags mentioned (chest pain, fever, dizziness, \
shortness of breath, missed medication, swelling, bleeding, etc.).
5. Decide if the answer is too unclear or ambiguous to record (needs_clarification=true) \
and if so, suggest a short clarifying follow-up question to ask the patient.

Respond ONLY with valid JSON matching this exact schema — no markdown fences, \
no commentary:
{
  "raw_speech": "<exact speech as given>",
  "interpreted_answer": "<clinical summary of what patient said>",
  "normalized": "<yes|no|scale_value|free_text_summary>",
  "clinical_flags": ["flag1", "flag2"],
  "needs_clarification": true|false,
  "clarification_question": "<question string or null>"
}

Rules:
- For yes_no questions, normalized must be exactly "yes" or "no".
- For scale questions (e.g. pain 1-10), normalized must be the number as a string.
- For open questions, normalized is a concise 1-sentence summary.
- clinical_flags entries use snake_case, e.g. "chest_pain", "fever", "missed_medication", \
"shortness_of_breath", "dizziness", "swelling", "bleeding", "fatigue".
- Only set needs_clarification=true if the speech is genuinely unintelligible or \
completely off-topic. Partial or hedging answers should still be interpreted.
- Keep clarification_question short and conversational (under 20 words).
"""


def _llm_interpret(
    question_text: str,
    question_type: str,
    speech_result: str,
    diagnosis: str,
) -> InterpretedResponse:
    """Synchronous Claude call — run via asyncio.to_thread."""
    from langchain_anthropic import ChatAnthropic

    settings = get_settings()
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=settings.anthropic_api_key,
        temperature=0,
        max_tokens=384,
        default_request_timeout=ANTHROPIC_HTTP_TIMEOUT_SEC,
    )

    user_prompt = (
        f"Patient diagnosis: {diagnosis}\n"
        f"Question asked: {question_text}\n"
        f"Question type: {question_type}\n"
        f"Patient's spoken response: {speech_result!r}"
    )

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = text.strip()

    if text.startswith("```"):
        newline = text.index("\n")
        text = text[newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    data = json.loads(text)
    return InterpretedResponse(**data)


async def interpret_speech_response(
    question_text: str,
    question_type: str,
    speech_result: str,
    diagnosis: str,
) -> InterpretedResponse:
    """Async wrapper — runs Claude synchronously in a thread pool."""
    if not speech_result.strip():
        logger.warning("interpret_speech_response.empty_speech")
        return InterpretedResponse(
            raw_speech=speech_result,
            interpreted_answer="No response detected",
            normalized="",
            clinical_flags=[],
            needs_clarification=True,
            clarification_question="I didn't catch that. Could you please repeat your answer?",
        )

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                _llm_interpret,
                question_text,
                question_type,
                speech_result,
                diagnosis,
            ),
            timeout=LLM_TIMEOUT_SEC,
        )
        logger.info(
            "interpret_speech_response.done",
            normalized=result.normalized,
            clinical_flags=result.clinical_flags,
            needs_clarification=result.needs_clarification,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(
            "interpret_speech_response.timeout",
            timeout_sec=LLM_TIMEOUT_SEC,
        )
        return InterpretedResponse(
            raw_speech=speech_result,
            interpreted_answer=speech_result,
            normalized=speech_result,
            clinical_flags=[],
            needs_clarification=False,
            clarification_question=None,
        )
    except Exception:
        logger.exception("interpret_speech_response.error")
        return InterpretedResponse(
            raw_speech=speech_result,
            interpreted_answer=speech_result,
            normalized=speech_result,
            clinical_flags=[],
            needs_clarification=False,
            clarification_question=None,
        )


# ---------------------------------------------------------------------------
# Appointment slot choice interpreter
# ---------------------------------------------------------------------------

class AppointmentChoice(BaseModel):
    chosen_slot_index: int | None = None
    preferred_time: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None


_APPT_SYSTEM_PROMPT = """\
You are an AI assistant helping a patient choose an appointment time over the phone.
The patient was offered numbered time slots and spoken a response.

Your job is to:
1. Determine if the patient selected one of the offered slots (by number, day, or time).
2. If they expressed a different preferred time (e.g. "Friday afternoon"), capture it.
3. If the response is too unclear, request clarification.

Respond ONLY with valid JSON — no markdown fences, no commentary:
{
  "chosen_slot_index": <0-based integer index of chosen slot, or null>,
  "preferred_time": "<patient's expressed preferred time if no slot chosen, or null>",
  "needs_clarification": true|false,
  "clarification_question": "<short follow-up question or null>"
}

Rules:
- chosen_slot_index is 0-based (Option 1 → 0, Option 2 → 1, Option 3 → 2).
- If patient says "option 1" / "the first one" / "Monday" (matching slot 1) → chosen_slot_index: 0.
- If patient says "none of these" / "what about Friday" → chosen_slot_index: null, preferred_time: "Friday".
- Only set needs_clarification=true if response is genuinely unintelligible.
"""


def _llm_interpret_appt_choice(
    speech_result: str,
    slots: list[dict[str, Any]],
) -> AppointmentChoice:
    """Synchronous Claude call — run via asyncio.to_thread."""
    from langchain_anthropic import ChatAnthropic

    settings = get_settings()
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=settings.anthropic_api_key,
        temperature=0,
        max_tokens=256,
        default_request_timeout=ANTHROPIC_HTTP_TIMEOUT_SEC,
    )

    slots_text = "\n".join(
        f"Option {i + 1} (index {i}): {s['slot_start']} with {s['doctor_name']}"
        for i, s in enumerate(slots)
    )
    user_prompt = (
        f"Offered slots:\n{slots_text}\n\n"
        f"Patient's spoken response: {speech_result!r}"
    )

    messages = [
        SystemMessage(content=_APPT_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = text.strip()
    if text.startswith("```"):
        newline = text.index("\n")
        text = text[newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    data = json.loads(text)
    return AppointmentChoice(**data)


async def interpret_appointment_choice(
    speech_result: str,
    slots: list[dict[str, Any]],
) -> AppointmentChoice:
    """Async wrapper for appointment slot choice interpretation."""
    if not speech_result.strip():
        return AppointmentChoice(
            needs_clarification=True,
            clarification_question="I didn't catch that. Which option would you prefer?",
        )

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_llm_interpret_appt_choice, speech_result, slots),
            timeout=LLM_TIMEOUT_SEC,
        )
        logger.info(
            "interpret_appointment_choice.done",
            chosen_slot_index=result.chosen_slot_index,
            preferred_time=result.preferred_time,
            needs_clarification=result.needs_clarification,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("interpret_appointment_choice.timeout")
        return AppointmentChoice(needs_clarification=True, clarification_question="Sorry, could you repeat which option you prefer?")
    except Exception:
        logger.exception("interpret_appointment_choice.error")
        return AppointmentChoice(needs_clarification=True, clarification_question="Could you please repeat which option works for you?")

from __future__ import annotations

from langchain_anthropic import ChatAnthropic

from shared.config import get_settings


def get_llm() -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=settings.anthropic_api_key,
        temperature=0,
        max_tokens=4096,
    )

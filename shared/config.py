from __future__ import annotations

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    anthropic_api_key: str

    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    twilio_webhook_base_url: str = "http://localhost:8002"

    # Infrastructure
    rabbitmq_url: str = "amqp://guest:guest@localhost/"
    redis_url: str = "redis://localhost:6379"
    database_url: str = "sqlite+aiosqlite:///./carebridge.db"

    # App
    demo_mode: bool = True
    # When demo_mode: first scheduled follow-up runs after this many seconds (default ~4 min).
    demo_followup_delay_seconds: int = 240
    # Chained follow-up spacing (minutes) when demo_mode — Brain schedule_event scheduled_at.
    demo_followup_minutes_low: int = 1
    demo_followup_minutes_medium: int = 2
    demo_followup_minutes_high: int = 3
    demo_followup_minutes_critical: int = 4

    # Service URLs (for inter-service HTTP calls)
    brain_agent_url: str = "http://localhost:8001"
    comm_agent_url: str = "http://localhost:8002"
    db_agent_url: str = "http://localhost:8003"
    scheduler_url: str = "http://localhost:8004"

    @field_validator(
        "anthropic_api_key",
        "twilio_account_sid",
        "twilio_auth_token",
        "twilio_phone_number",
        "twilio_webhook_base_url",
        "rabbitmq_url",
        "redis_url",
        "database_url",
        "brain_agent_url",
        "comm_agent_url",
        "db_agent_url",
        "scheduler_url",
        mode="before",
    )
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


def get_settings() -> Settings:
    return Settings()

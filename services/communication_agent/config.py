from __future__ import annotations

from shared.config import Settings, get_settings

SERVICE_NAME = "communication_agent"
SERVICE_PORT = 8002


class CommAgentSettings:
    """Convenience accessor for communication-agent specific settings."""

    @property
    def settings(self) -> Settings:
        # Reload from the environment each time so .env / TWILIO_WEBHOOK_BASE_URL changes
        # apply without restarting the process (important when ngrok assigns a new URL).
        return get_settings()

    @property
    def twilio_account_sid(self) -> str:
        return self.settings.twilio_account_sid

    @property
    def twilio_auth_token(self) -> str:
        return self.settings.twilio_auth_token

    @property
    def twilio_phone_number(self) -> str:
        return self.settings.twilio_phone_number

    @property
    def twilio_webhook_base_url(self) -> str:
        return self.settings.twilio_webhook_base_url

    @property
    def brain_agent_url(self) -> str:
        return self.settings.brain_agent_url

    @property
    def db_agent_url(self) -> str:
        return self.settings.db_agent_url

    @property
    def redis_url(self) -> str:
        return self.settings.redis_url

    @property
    def rabbitmq_url(self) -> str:
        return self.settings.rabbitmq_url

    @property
    def demo_mode(self) -> bool:
        return self.settings.demo_mode


comm_settings = CommAgentSettings()

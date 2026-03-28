from __future__ import annotations

from shared.config import Settings, get_settings

SERVICE_NAME = "brain_agent"
SERVICE_PORT = 8001


class BrainAgentSettings:
    """Convenience accessor for brain-agent specific settings."""

    def __init__(self) -> None:
        self._settings: Settings | None = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def anthropic_api_key(self) -> str:
        return self.settings.anthropic_api_key

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


brain_settings = BrainAgentSettings()

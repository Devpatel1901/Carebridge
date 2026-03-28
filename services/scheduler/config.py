from __future__ import annotations

from shared.config import Settings, get_settings

SERVICE_NAME = "scheduler"
SERVICE_PORT = 8004


class SchedulerSettings:
    """Convenience accessor for scheduler-specific settings."""

    def __init__(self) -> None:
        self._settings: Settings | None = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def comm_agent_url(self) -> str:
        return self.settings.comm_agent_url

    @property
    def db_agent_url(self) -> str:
        return self.settings.db_agent_url

    @property
    def rabbitmq_url(self) -> str:
        return self.settings.rabbitmq_url

    @property
    def demo_mode(self) -> bool:
        return self.settings.demo_mode


scheduler_settings = SchedulerSettings()

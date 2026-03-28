from __future__ import annotations

from shared.config import Settings, get_settings

SERVICE_NAME = "db_agent"


class DbAgentSettings(Settings):
    service_name: str = SERVICE_NAME
    db_agent_port: int = 8003


def get_db_agent_settings() -> DbAgentSettings:
    return DbAgentSettings()

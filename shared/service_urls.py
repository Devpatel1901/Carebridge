"""Service base URLs for CLI scripts (localhost, Docker Compose DNS, or tunnels)."""
from __future__ import annotations

import os


def _url(env_name: str, default: str) -> str:
    return (os.environ.get(env_name) or default).strip().rstrip("/")


def brain_agent_url() -> str:
    return _url("BRAIN_AGENT_URL", "http://localhost:8001")


def comm_agent_url() -> str:
    return _url("COMM_AGENT_URL", "http://localhost:8002")


def db_agent_url() -> str:
    return _url("DB_AGENT_URL", "http://localhost:8003")


def scheduler_url() -> str:
    return _url("SCHEDULER_URL", "http://localhost:8004")


def frontend_url() -> str:
    return _url("FRONTEND_URL", "http://localhost:3000")

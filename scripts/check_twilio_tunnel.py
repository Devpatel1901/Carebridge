"""Verify TWILIO_WEBHOOK_BASE_URL returns TwiML (not ngrok HTML) from the public internet.

Usage (from repo root, with .env present):

  uv run python scripts/check_twilio_tunnel.py

Exits 0 only if the smoke endpoint body looks like XML TwiML.
"""
from __future__ import annotations

import asyncio
import sys

import httpx

from services.communication_agent.ngrok_compat import (
    SKIP_QUERY_KEY,
    SKIP_QUERY_VAL,
    ngrok_free_skip_warning_params,
)
from shared.config import get_settings


async def main() -> None:
    s = get_settings()
    base = s.twilio_webhook_base_url.strip().rstrip("/")
    path = "/webhooks/voice/twiml-smoke"
    url_plain = f"{base}{path}"
    extra = ngrok_free_skip_warning_params(base)
    url_twilio_like = f"{base}{path}?{SKIP_QUERY_KEY}={SKIP_QUERY_VAL}" if extra else url_plain

    print(f"Checking: {url_plain[:80]}{'…' if len(url_plain) > 80 else ''}")

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        # Mimic Twilio: no special headers
        r1 = await client.get(url_plain)
        body1 = (r1.text or "")[:500]
        ok1 = r1.status_code == 200 and "<?xml" in body1 and "<Response>" in body1

        r2 = await client.get(url_twilio_like)
        body2 = (r2.text or "")[:500]
        ok2 = r2.status_code == 200 and "<?xml" in body2 and "<Response>" in body2

    if ok1:
        print("[PASS] Plain GET returns TwiML — Twilio should be able to fetch webhooks.")
        sys.exit(0)

    if ok2 and not ok1:
        print(
            "[WARN] Plain GET did not return TwiML, but URL with ngrok skip param did.\n"
            "       Ensure COMM_AGENT_URL uses ngrok-free compat (query param is auto-added in code)."
        )
        print(f"       status={r1.status_code} snippet={body1[:120]!r}")
        sys.exit(0)

    print(f"[FAIL] Expected TwiML XML. status={r1.status_code}")
    print(f"       body snippet: {body1[:200]!r}")
    if r1.status_code != r2.status_code or body1 != body2:
        print(f"       (with skip param) status={r2.status_code} snippet={body2[:120]!r}")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

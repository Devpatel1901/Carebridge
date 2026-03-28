from __future__ import annotations

import asyncio
from functools import lru_cache

from twilio.rest import Client as TwilioClient

from shared.config import get_settings
from shared.logging import get_logger

logger = get_logger("twilio_client")


@lru_cache(maxsize=1)
def get_twilio_client() -> TwilioClient:
    settings = get_settings()
    return TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)


async def make_voice_call(
    to: str,
    twiml_url: str,
    status_callback_url: str | None = None,
) -> str:
    """
    Initiate an outbound voice call via Twilio.
    Returns the call SID.
    """
    settings = get_settings()
    client = get_twilio_client()

    def _call() -> str:
        kwargs: dict = {
            "to": to,
            "from_": settings.twilio_phone_number,
            "url": twiml_url,
            "method": "GET",
        }
        if status_callback_url:
            kwargs["status_callback"] = status_callback_url
            kwargs["status_callback_method"] = "POST"
            kwargs["status_callback_event"] = [
                "initiated",
                "ringing",
                "answered",
                "completed",
                "no-answer",
                "busy",
                "failed",
                "canceled",
            ]
        call = client.calls.create(**kwargs)
        return call.sid

    sid = await asyncio.to_thread(_call)
    logger.info("voice_call_initiated", to=to, call_sid=sid)
    return sid

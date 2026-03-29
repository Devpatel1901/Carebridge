"""ElevenLabs TTS integration for the Communication Agent.

Exposes:
- tts_speak_url(text) -> str        : builds the public <Play> URL for TwiML
- router                            : FastAPI router with GET /voice/tts endpoint
"""
from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.communication_agent.ngrok_compat import ngrok_free_skip_warning_params
from shared.config import get_settings
from shared.logging import get_logger

logger = get_logger("elevenlabs_tts")

router = APIRouter()

# ElevenLabs model — eleven_turbo_v2_5 gives the lowest latency (~300 ms first byte)
_TTS_MODEL = "eleven_turbo_v2_5"


def tts_speak_url(text: str) -> str:
    """Return the public HTTPS URL Twilio should <Play> to speak `text`."""
    settings = get_settings()
    base = settings.twilio_webhook_base_url.strip().rstrip("/")
    q: dict[str, str] = {
        **ngrok_free_skip_warning_params(base),
        "text": text,
    }
    return f"{base}/voice/tts?{urlencode(q)}"


@router.get("/voice/tts")
async def voice_tts_endpoint(text: str = "") -> StreamingResponse:
    """Stream ElevenLabs TTS audio for `text` so Twilio can <Play> it.

    Returns audio/mpeg via streaming so Twilio starts playback as soon as the
    first bytes arrive — no full-buffer wait.  On any ElevenLabs error the
    endpoint returns an empty 200 with the right content-type so Twilio skips
    silently rather than erroring the call.
    """
    settings = get_settings()

    if not text:
        return StreamingResponse(iter([]), media_type="audio/mpeg")

    if not settings.elevenlabs_api_key:
        logger.warning("voice_tts.no_api_key")
        return StreamingResponse(iter([]), media_type="audio/mpeg")

    try:
        from elevenlabs import AsyncElevenLabs

        client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)

        # .stream() returns an async generator — do NOT await it
        audio_gen = client.text_to_speech.stream(
            text=text,
            voice_id=settings.elevenlabs_voice_id,
            model_id=_TTS_MODEL,
        )

        async def _generate():
            async for chunk in audio_gen:
                if chunk:
                    yield chunk

        return StreamingResponse(_generate(), media_type="audio/mpeg")

    except Exception:
        logger.exception("voice_tts.error", text_len=len(text))
        return StreamingResponse(iter([]), media_type="audio/mpeg")

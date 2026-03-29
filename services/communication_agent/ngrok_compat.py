"""ngrok free-tier tunnels (ngrok-free.*) may return an HTML warning page unless the
request includes `ngrok-skip-browser-warning`. Twilio cannot set custom headers on
webhook fetches, but including the same token as a query parameter is often honored
at the edge so Twilio receives real TwiML instead of HTML (which causes Twilio's
generic application error).
"""
from __future__ import annotations


SKIP_QUERY_KEY = "ngrok-skip-browser-warning"
SKIP_QUERY_VAL = "1"


def ngrok_free_skip_warning_params(public_base_url: str) -> dict[str, str]:
    """Extra query params to append to webhook URLs when using ngrok-free hosts."""
    if "ngrok-free." in (public_base_url or "").lower():
        return {SKIP_QUERY_KEY: SKIP_QUERY_VAL}
    return {}

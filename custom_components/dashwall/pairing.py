"""Pairing through the kiosk's dashboard login.

The setup flow sends the kiosk a nonce. The kiosk posts it back, with its new
token, to the Home Assistant its dashboard is logged in to, using that
dashboard session. This view only accepts logged-in users, so a kiosk pairs
only with a Home Assistant someone at the kiosk can log in to, and the token
never goes anywhere else.
"""

from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import Any

from aiohttp import web

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.http import KEY_HASS, HomeAssistantView

from .const import DOMAIN

PENDING: str = f"{DOMAIN}_pending_pairings"
VIEW_REGISTERED: str = f"{DOMAIN}_pair_view"


@callback
def async_expect_pairing(hass: HomeAssistant, nonce: str) -> asyncio.Future[dict[str, Any]]:
    """Register a nonce; the future resolves when the kiosk confirms it."""
    if not hass.data.get(VIEW_REGISTERED):
        hass.http.register_view(PairConfirmView())
        hass.data[VIEW_REGISTERED] = True
    future: asyncio.Future[dict[str, Any]] = hass.loop.create_future()
    hass.data.setdefault(PENDING, {})[nonce] = future
    return future


@callback
def async_forget_pairing(hass: HomeAssistant, nonce: str) -> None:
    hass.data.get(PENDING, {}).pop(nonce, None)


class PairConfirmView(HomeAssistantView):
    """Receives a kiosk's pairing confirmation, sent with a user's login."""

    url = "/api/dashwall/pair_confirm"
    name = "api:dashwall:pair_confirm"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass = request.app[KEY_HASS]
        try:
            body = await request.json()
        except ValueError:
            return self.json_message("Body is not JSON", HTTPStatus.BAD_REQUEST)
        nonce, token, device_id = body.get("nonce"), body.get("token"), body.get("id")
        future = hass.data.get(PENDING, {}).get(nonce) if isinstance(nonce, str) else None
        if future is None or future.done():
            return self.json_message("Unknown or expired pairing request", HTTPStatus.NOT_FOUND)
        if not isinstance(token, str) or len(token) < 32 or not isinstance(device_id, str):
            return self.json_message("Token and id required", HTTPStatus.BAD_REQUEST)
        future.set_result({"token": token, "id": device_id, "user": request["hass_user"].name})
        return self.json({"ok": True})

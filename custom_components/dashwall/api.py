"""Client for the kiosk app's local HTTP API."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
import time
from typing import Any

import aiohttp

from .signing import sign, signing_key

# Every request identifies itself; the app turns away anything else.
CLIENT = "dashwall-ha/0.3.0"
SIGNED_PATHS = {"/api/state", "/api/events", "/api/command"}


class KioskApiError(Exception):
    """The kiosk app could not be reached or answered with an error."""


class KioskAuthError(KioskApiError):
    """The kiosk app refused our signature (key forgotten on the tablet, or clocks far apart)."""


class KioskBusy(KioskApiError):
    """The kiosk is already waiting to finish another pairing request."""


class KioskApi:
    """Talks to one kiosk tablet. Signs requests with the key derived from the pairing token."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str | None = None) -> None:
        self._session = session
        self.host = host
        self.port = port
        self._key = signing_key(token) if token else None

    @property
    def base_url(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}"

    def _headers(self, method: str, path: str, body: bytes) -> dict[str, str]:
        headers = {"X-Kiosk-Client": CLIENT, "Content-Type": "application/json"}
        if path in SIGNED_PATHS and self._key:
            now = int(time.time())
            headers["X-Kiosk-Time"] = str(now)
            headers["X-Kiosk-Signature"] = sign(self._key, method, path, now, body)
        return headers

    async def _request(self, method: str, path: str, *, body: dict[str, Any] | None = None, timeout: float = 10) -> dict[str, Any]:
        data = json.dumps(body, separators=(",", ":")).encode() if body is not None else b""
        try:
            async with self._session.request(
                method,
                self.base_url + path,
                data=data or None,
                headers=self._headers(method, path, data),
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                result = await resp.json(content_type=None)
                if resp.status == 401:
                    raise KioskAuthError(result.get("error", "signature refused"))
                if resp.status == 409:
                    raise KioskBusy(result.get("error", "busy"))
                if resp.status >= 400:
                    raise KioskApiError(result.get("error", f"HTTP {resp.status}"))
                return result
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, AttributeError) as err:
            raise KioskApiError(f"{type(err).__name__}: {err}") from err

    async def info(self) -> dict[str, Any]:
        """Who the kiosk is. Needs no key."""
        return await self._request("GET", "/api/info")

    async def pair(self, name: str, url: str | None, nonce: str) -> dict[str, Any]:
        """Ask to pair. Returns at once; the kiosk confirms the nonce later
        through its dashboard login (see pairing.PairConfirmView)."""
        return await self._request("POST", "/api/pair", body={"name": name, "url": url or "", "nonce": nonce})

    async def state(self) -> dict[str, Any]:
        return await self._request("GET", "/api/state")

    async def command(self, command: str, **params: Any) -> None:
        await self._request("POST", "/api/command", body={"command": command, **params})

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield the kiosk's state as it changes (Server-Sent Events).

        The app sends the state on every change and once a minute, and a ping
        comment every 20 s; no data for 75 s means the stream is dead.
        """
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=75)
        try:
            async with self._session.get(
                self.base_url + "/api/events", headers=self._headers("GET", "/api/events", b""), timeout=timeout
            ) as resp:
                if resp.status == 401:
                    raise KioskAuthError("signature refused")
                if resp.status != 200:
                    raise KioskApiError(f"HTTP {resp.status}")
                async for raw in resp.content:
                    line = raw.decode("utf-8", "replace").strip()
                    if line.startswith("data:"):
                        yield json.loads(line[5:].strip())
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise KioskApiError(f"{type(err).__name__}: {err}") from err

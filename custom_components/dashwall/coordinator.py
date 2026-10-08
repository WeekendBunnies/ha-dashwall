"""Keeps one kiosk's state current: an event stream, with polling as a fallback."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import KioskApi, KioskApiError, KioskAuthError
from .const import LOGGER

type KioskConfigEntry = ConfigEntry[KioskCoordinator]


class KioskCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """State of one kiosk tablet."""

    config_entry: KioskConfigEntry

    def __init__(self, hass: HomeAssistant, entry: KioskConfigEntry, api: KioskApi) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=entry.title,
            # The event stream pushes every change; polling is only a fallback.
            update_interval=timedelta(minutes=5),
        )
        self.api = api
        self.last_seen: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.api.state()
        except KioskAuthError as err:
            raise ConfigEntryAuthFailed(f"The kiosk no longer knows this Home Assistant: {err}") from err
        except KioskApiError as err:
            raise UpdateFailed(f"Kiosk not reachable: {err}") from err
        self.last_seen = dt_util.utcnow()
        return data

    async def async_listen(self) -> None:
        """Keep the kiosk's event stream open for as long as the entry is loaded."""
        delay = 1.0
        while True:
            got_data = False
            try:
                async for state in self.api.events():
                    got_data = True
                    delay = 1.0
                    self.last_seen = dt_util.utcnow()
                    self.async_set_updated_data(state)
            except KioskAuthError:
                # Forgotten on the tablet: a refresh raises ConfigEntryAuthFailed,
                # which starts re-pairing.
                await self.async_request_refresh()
                return
            except KioskApiError as err:
                LOGGER.debug("Event stream from %s ended: %s", self.api.host, err)
                if not got_data:
                    self.async_set_update_error(err)
            # A stream that worked is reopened at once; a failing one backs off.
            await asyncio.sleep(1.0 if got_data else delay)
            if not got_data:
                delay = min(delay * 2, 30.0)

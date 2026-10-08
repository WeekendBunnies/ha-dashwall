"""Base entity for a kiosk tablet."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import KioskApiError
from .const import DOMAIN, MANUFACTURER
from .coordinator import KioskCoordinator


class KioskEntity(CoordinatorEntity[KioskCoordinator]):
    """An entity of one kiosk tablet."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: KioskCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        data = coordinator.data or {}
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.unique_id))},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=f"Kiosk on {data.get('model', 'Android')}",
            sw_version=data.get("version"),
        )

    async def _command(self, command: str, **params: Any) -> None:
        try:
            await self.coordinator.api.command(command, **params)
        except KioskApiError as err:
            raise HomeAssistantError(f"The kiosk did not accept '{command}': {err}") from err

    async def _set(self, key: str, value: Any) -> None:
        """Change a kiosk setting, and show it at once instead of waiting for the push."""
        await self._command("set", key=key, value=value)
        self.coordinator.async_set_updated_data({**(self.coordinator.data or {}), key: value})

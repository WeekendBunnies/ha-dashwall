"""Dashboard URL, settable from Home Assistant."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KioskConfigEntry, KioskCoordinator
from .entity import KioskEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: KioskConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([KioskDashboardUrl(entry.runtime_data)])


class KioskDashboardUrl(KioskEntity, TextEntity):
    """The page the kiosk shows; the kiosk loads it again when it changes."""

    _attr_name = "Dashboard URL"
    _attr_icon = "mdi:web"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_max = 255
    _attr_pattern = r"https?://.+"

    def __init__(self, coordinator: KioskCoordinator) -> None:
        super().__init__(coordinator, "dashboard_url")

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data or {}).get("dashboard_url")

    async def async_set_value(self, value: str) -> None:
        await self._set("dashboard_url", value.strip())

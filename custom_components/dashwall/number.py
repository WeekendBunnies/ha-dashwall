"""Page zoom, settable from Home Assistant."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KioskConfigEntry, KioskCoordinator
from .entity import KioskEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: KioskConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([KioskPageZoom(entry.runtime_data)])


class KioskPageZoom(KioskEntity, NumberEntity):
    """Scales the whole dashboard, like the Home Assistant app's "Page zoom"."""

    _attr_name = "Page zoom"
    _attr_icon = "mdi:magnify-plus-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 50
    _attr_native_max_value = 200
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: KioskCoordinator) -> None:
        super().__init__(coordinator, "page_zoom")

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("page_zoom")

    async def async_set_native_value(self, value: float) -> None:
        await self._set("page_zoom", int(value))

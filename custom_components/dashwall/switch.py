"""Kiosk mode and power settings, settable from Home Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KioskConfigEntry, KioskCoordinator
from .entity import KioskEntity

SWITCHES = (
    SwitchEntityDescription(
        key="kiosk_mode",
        name="Kiosk mode",
        icon="mdi:fullscreen",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key="keep_cpu_awake",
        name="Keep CPU awake",
        icon="mdi:chip",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key="wifi_full_power",
        name="Wi-Fi full power",
        icon="mdi:wifi-strength-4",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: KioskConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(KioskSwitch(entry.runtime_data, d) for d in SWITCHES)


class KioskSwitch(KioskEntity, SwitchEntity):
    """A setting of the kiosk app that Home Assistant can switch."""

    def __init__(self, coordinator: KioskCoordinator, description: SwitchEntityDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return (self.coordinator.data or {}).get(self.entity_description.key)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(self.entity_description.key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(self.entity_description.key, False)

"""Binary sensors: connected, screen, dashboard, charging, charger."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KioskConfigEntry, KioskCoordinator
from .entity import KioskEntity


@dataclass(frozen=True, kw_only=True)
class KioskBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]


def _dashboard(data: dict[str, Any]) -> bool | None:
    # "paused": the screen is off, and the frontend closes its connection on
    # purpose while hidden, so neither on nor off would be true.
    state = data.get("dashboard")
    return None if state == "paused" else state == "connected"


SENSORS = (
    KioskBinaryDescription(key="screen", name="Screen", icon="mdi:tablet", value_fn=lambda d: d.get("screen_on")),
    KioskBinaryDescription(
        key="dashboard",
        name="Dashboard connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=_dashboard,
    ),
    KioskBinaryDescription(
        key="charging",
        name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: d.get("charging"),
    ),
    KioskBinaryDescription(
        key="plugged_in",
        name="Charger connected",
        device_class=BinarySensorDeviceClass.PLUG,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("plugged_in"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: KioskConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([KioskConnected(coordinator), *(KioskBinarySensor(coordinator, d) for d in SENSORS)])


class KioskBinarySensor(KioskEntity, BinarySensorEntity):
    entity_description: KioskBinaryDescription

    def __init__(self, coordinator: KioskCoordinator, description: KioskBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data or {})


class KioskConnected(KioskEntity, BinarySensorEntity):
    """Whether Home Assistant can reach the kiosk app. Never unavailable itself."""

    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: KioskCoordinator) -> None:
        super().__init__(coordinator, "connected")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success

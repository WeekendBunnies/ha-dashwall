"""Sensors: battery details, dashboard state, reloads, last event, version, last seen."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KioskConfigEntry, KioskCoordinator
from .entity import KioskEntity


@dataclass(frozen=True, kw_only=True)
class KioskSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS = (
    KioskSensorDescription(
        key="battery",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("battery"),
    ),
    # The battery details below match the Home Assistant app's battery sensors.
    KioskSensorDescription(
        key="battery_state",
        name="Battery state",
        translation_key="battery_state",
        device_class=SensorDeviceClass.ENUM,
        options=["charging", "discharging", "full", "not_charging", "unknown"],
        value_fn=lambda d: d.get("battery_state"),
    ),
    KioskSensorDescription(
        key="battery_temperature",
        name="Battery temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.get("battery_temperature"),
    ),
    KioskSensorDescription(
        key="battery_power",
        name="Battery power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.get("battery_power"),
    ),
    KioskSensorDescription(
        key="remaining_charge_time",
        name="Remaining charge time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda d: d.get("remaining_charge_time"),
    ),
    KioskSensorDescription(
        key="charger_type",
        name="Charger type",
        translation_key="charger_type",
        device_class=SensorDeviceClass.ENUM,
        options=["none", "ac", "usb", "wireless", "dock", "unknown"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("charger_type"),
    ),
    KioskSensorDescription(
        key="battery_health",
        name="Battery health",
        translation_key="battery_health",
        device_class=SensorDeviceClass.ENUM,
        options=["good", "overheated", "dead", "over_voltage", "failed", "cold", "unknown"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("battery_health"),
    ),
    KioskSensorDescription(
        key="dashboard_state",
        name="Dashboard state",
        icon="mdi:web",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("dashboard"),
    ),
    KioskSensorDescription(
        key="reloads",
        name="Dashboard reloads",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("reloads"),
    ),
    KioskSensorDescription(
        key="last_reload",
        name="Last reload reason",
        icon="mdi:refresh-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("last_reload") or None,
    ),
    KioskSensorDescription(
        key="last_event",
        name="Last event",
        icon="mdi:text-box-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (d.get("last_event") or "")[:255] or None,
    ),
    KioskSensorDescription(
        key="version",
        name="App version",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("version"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: KioskConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([KioskLastSeen(coordinator), *(KioskSensor(coordinator, d) for d in SENSORS)])


class KioskSensor(KioskEntity, SensorEntity):
    entity_description: KioskSensorDescription

    def __init__(self, coordinator: KioskCoordinator, description: KioskSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})


class KioskLastSeen(KioskEntity, SensorEntity):
    """When Home Assistant last heard from the kiosk; keeps its value while offline."""

    _attr_name = "Last seen"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: KioskCoordinator) -> None:
        super().__init__(coordinator, "last_seen")

    @property
    def available(self) -> bool:
        return self.coordinator.last_seen is not None

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_seen

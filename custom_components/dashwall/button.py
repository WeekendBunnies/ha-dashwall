"""Buttons: wake the screen, reload the dashboard."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KioskConfigEntry, KioskCoordinator
from .entity import KioskEntity


@dataclass(frozen=True, kw_only=True)
class KioskButtonDescription(ButtonEntityDescription):
    command: str


BUTTONS = (
    KioskButtonDescription(key="wake", name="Wake screen", icon="mdi:monitor-shimmer", command="wake"),
    KioskButtonDescription(key="reload", name="Reload dashboard", icon="mdi:refresh", command="reload"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: KioskConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(KioskButton(entry.runtime_data, d) for d in BUTTONS)


class KioskButton(KioskEntity, ButtonEntity):
    entity_description: KioskButtonDescription

    def __init__(self, coordinator: KioskCoordinator, description: KioskButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self._command(self.entity_description.command)

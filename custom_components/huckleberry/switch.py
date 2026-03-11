"""Switch platform for Huckleberry integration."""
from __future__ import annotations

from typing import cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HuckleberryEntryData
from .const import DOMAIN
from .features.nursing import build_nursing_switches
from .features.sleep import build_sleep_switches


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Huckleberry switches."""
    entry_data = cast(HuckleberryEntryData, hass.data[DOMAIN][entry.entry_id])
    entities: list[SwitchEntity] = []

    entities.extend(build_sleep_switches(entry_data["coordinator"], entry_data["api"], entry_data["children"]))
    entities.extend(build_nursing_switches(entry_data["coordinator"], entry_data["api"], entry_data["children"]))

    async_add_entities(entities)


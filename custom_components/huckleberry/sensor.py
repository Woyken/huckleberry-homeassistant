"""Sensor platform for Huckleberry."""
from __future__ import annotations

from typing import cast

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HuckleberryEntryData
from .const import DOMAIN
from .features.activity import (
    build_activity_sensors,
    setup_activity_sensor_activation,
)
from .features.bottle import build_bottle_sensors
from .features.child import build_child_sensors
from .features.diaper import build_diaper_sensors
from .features.growth import build_growth_sensors
from .features.medication import build_medication_sensors
from .features.nursing import build_nursing_sensors
from .features.potty import build_potty_sensors
from .features.pumping import build_pumping_sensors
from .features.sleep import build_sleep_sensors
from .features.solids import build_solids_sensors
from .features.sweetspot import build_sweetspot_sensors


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Huckleberry sensors."""
    entry_data = cast(HuckleberryEntryData, hass.data[DOMAIN][entry.entry_id])
    coordinator = entry_data["coordinator"]
    entities: list[SensorEntity] = []
    entities.extend(build_child_sensors(coordinator, entry_data["children"]))
    entities.extend(build_growth_sensors(coordinator, entry_data["children"]))
    entities.extend(build_medication_sensors(coordinator, entry_data["children"]))
    entities.extend(build_diaper_sensors(coordinator, entry_data["children"]))
    entities.extend(build_potty_sensors(coordinator, entry_data["children"]))
    entities.extend(build_bottle_sensors(coordinator, entry_data["children"]))
    entities.extend(build_solids_sensors(coordinator, entry_data["children"]))
    entities.extend(build_nursing_sensors(coordinator, entry_data["children"]))
    entities.extend(build_pumping_sensors(coordinator, entry_data["children"]))
    entities.extend(build_sleep_sensors(coordinator, entry_data["children"]))
    activity_sensors = build_activity_sensors(coordinator, entry_data["children"])
    entities.extend(activity_sensors)
    entities.extend(build_sweetspot_sensors(coordinator, entry_data["children"]))

    async_add_entities(entities)

    setup_activity_sensor_activation(
        hass,
        entry,
        coordinator,
        entry_data["children"],
        activity_sensors,
        async_add_entities,
    )

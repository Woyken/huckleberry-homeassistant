"""Sensor platform for Huckleberry."""
from __future__ import annotations

from typing import cast

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from huckleberry_api.firebase_types import ActivityMode

from . import HuckleberryEntryData
from .const import DOMAIN
from .features.activity import HuckleberryActivitySensor, build_activity_sensors
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

    last_activity_sensors = [
        entity
        for entity in activity_sensors
        if isinstance(entity, HuckleberryActivitySensor)
    ]
    children_by_uid = {child.uid: child for child in entry_data["children"]}
    handled_modes: set[tuple[str, ActivityMode]] = set()
    ready = False
    registry = er.async_get(hass)

    @callback
    def _async_sync_activity_sensors() -> None:
        """Enable and add activity sensors whose mode has a completed session."""
        if entry.pref_disable_new_entities:
            return

        new_entities: list[SensorEntity] = []
        for entity in last_activity_sensors:
            unique_id = entity.unique_id
            mode_key = (entity.child_uid, entity.mode)
            if unique_id is None or mode_key in handled_modes or not entity.has_activity_entry:
                continue

            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id is None:
                continue

            registry_entry = registry.async_get(entity_id)
            if registry_entry is None:
                continue
            if registry_entry.disabled_by is RegistryEntryDisabler.INTEGRATION:
                registry.async_update_entity(entity_id, disabled_by=None)
            elif registry_entry.disabled_by is not None:
                handled_modes.add(mode_key)
                continue
            elif hass.states.get(entity_id) is not None:
                handled_modes.add(mode_key)
                continue

            handled_modes.add(mode_key)
            child = children_by_uid.get(entity.child_uid)
            if child is not None:
                new_entities.append(
                    HuckleberryActivitySensor(coordinator, child, entity.mode)
                )

        if new_entities:
            async_add_entities(new_entities)

    @callback
    def _async_sync_if_ready() -> None:
        if ready:
            _async_sync_activity_sensors()

    entry.async_on_unload(coordinator.async_add_listener(_async_sync_if_ready))

    async def _async_initial_activity_sync() -> None:
        """Apply activity data after the platform has registered its entities."""
        nonlocal ready
        await hass.async_block_till_done()
        ready = True
        _async_sync_activity_sensors()

    hass.async_create_task(_async_initial_activity_sync())

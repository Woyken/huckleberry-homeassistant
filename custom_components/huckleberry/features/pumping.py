"""Pumping-related entities for Huckleberry."""
from __future__ import annotations

from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_iso8601_datetime, as_iso8601_duration

PUMP_STATE_OPTIONS: Final[list[str]] = ["active", "paused", "none"]


def build_pumping_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build pumping-related sensors."""
    entities: list[SensorEntity] = []
    for child in children:
        entities.append(HuckleberryPumpingSensor(coordinator, child))
    return entities


class HuckleberryPumpingSensor(HuckleberryBaseEntity, SensorEntity):
    """Representation of a Huckleberry pumping session sensor."""

    _attr_icon = "mdi:mother-nurse"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PUMP_STATE_OPTIONS
    _attr_translation_key = "pumping"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_pumping"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        pump_status = self.coordinator.get_pump_status(self.child_uid)
        timer = pump_status.timer if pump_status is not None else None
        if timer is None:
            return "none"
        if not timer.active:
            return "none"
        return "paused" if timer.paused else "active"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        pump_status = self.coordinator.get_pump_status(self.child_uid)
        if pump_status is None:
            return {}

        timer = pump_status.timer
        prefs = pump_status.prefs
        attributes: dict[str, object] = {}

        if timer is not None and timer.active:
            if timer.startTime is not None:
                attributes["current_start"] = as_iso8601_datetime(timer.startTime)
            if timer.entryMode is not None:
                attributes["current_entry_mode"] = timer.entryMode
            if timer.units is not None:
                attributes["current_units"] = timer.units

        last_pump = prefs.lastPump if prefs is not None else None
        if last_pump is not None:
            if last_pump.start is not None:
                attributes["previous_start"] = as_iso8601_datetime(last_pump.start)
            if last_pump.duration is not None:
                attributes["previous_duration"] = as_iso8601_duration(last_pump.duration)
            if last_pump.entryMode is not None:
                attributes["previous_entry_mode"] = last_pump.entryMode
            if last_pump.leftAmount is not None:
                attributes["previous_left_amount"] = last_pump.leftAmount
            if last_pump.rightAmount is not None:
                attributes["previous_right_amount"] = last_pump.rightAmount
            if last_pump.leftAmount is not None and last_pump.rightAmount is not None:
                attributes["previous_total_amount"] = last_pump.leftAmount + last_pump.rightAmount
            if last_pump.units is not None:
                attributes["previous_units"] = last_pump.units

        return attributes

"""Pumping-related entities for Huckleberry."""
from __future__ import annotations

from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_datetime, as_iso8601_datetime, as_iso8601_duration

PUMP_STATE_OPTIONS: Final[list[str]] = ["active", "paused", "none"]


def build_pumping_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build pumping-related sensors."""
    entities: list[SensorEntity] = []
    for child in children:
        entities.append(HuckleberryPumpingSensor(coordinator, child))
        entities.append(HuckleberryLastPumpSensor(coordinator, child))
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
            return None
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
        attributes: dict[str, object] = {}

        if timer is not None and timer.active:
            if timer.startTime is not None:
                attributes["current_start"] = as_iso8601_datetime(timer.startTime)
            if timer.entryMode is not None:
                attributes["current_entry_mode"] = timer.entryMode
            if timer.units is not None:
                attributes["current_units"] = timer.units

        return attributes


class HuckleberryLastPumpSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last completed pump session information."""

    _attr_icon = "mdi:baby-bottle-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_pump"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_last_pump"

    def _last_pump(self):
        pump_status = self.coordinator.get_pump_status(self.child_uid)
        prefs = pump_status.prefs if pump_status is not None else None
        return prefs.lastPump if prefs is not None else None

    @property
    def native_value(self):
        """Return the last pump session timestamp."""
        last_pump = self._last_pump()
        return as_datetime(last_pump.start if last_pump is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return last pump session attributes."""
        last_pump = self._last_pump()
        if last_pump is None:
            return {}

        attributes: dict[str, object] = {}
        if last_pump.start is not None:
            attributes["time"] = as_iso8601_datetime(last_pump.start)
        if last_pump.duration is not None:
            attributes["duration"] = as_iso8601_duration(last_pump.duration)
        if last_pump.entryMode is not None:
            attributes["entry_mode"] = last_pump.entryMode
        if last_pump.leftAmount is not None:
            attributes["left_amount"] = last_pump.leftAmount
        if last_pump.rightAmount is not None:
            attributes["right_amount"] = last_pump.rightAmount
        if last_pump.leftAmount is not None and last_pump.rightAmount is not None:
            attributes["total_amount"] = last_pump.leftAmount + last_pump.rightAmount
        if last_pump.units is not None:
            attributes["units"] = last_pump.units

        return attributes

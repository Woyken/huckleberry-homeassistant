"""Diaper-related sensors for Huckleberry."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_datetime, as_iso8601_datetime


def build_diaper_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build diaper sensors."""
    return [HuckleberryDiaperSensor(coordinator, child) for child in children]


class HuckleberryDiaperSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last diaper change information."""

    _attr_icon = "mdi:baby"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Diaper"
        self._attr_unique_id = f"{self.child_uid}_diaper"

    @property
    def native_value(self):
        """Return the last diaper change timestamp."""
        diaper_status = self.coordinator.get_diaper_status(self.child_uid)
        prefs = diaper_status.prefs if diaper_status is not None else None
        last_diaper = prefs.lastDiaper if prefs is not None else None

        return as_datetime(last_diaper.start if last_diaper is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return diaper change attributes."""
        diaper_status = self.coordinator.get_diaper_status(self.child_uid)
        prefs = diaper_status.prefs if diaper_status is not None else None
        last_diaper = prefs.lastDiaper if prefs is not None else None
        if last_diaper is None:
            return {}

        attributes: dict[str, object] = {}
        if last_diaper.start is not None:
            attributes["time"] = as_iso8601_datetime(last_diaper.start)
        if last_diaper.mode is not None:
            attributes["type"] = last_diaper.mode.title()
        return attributes

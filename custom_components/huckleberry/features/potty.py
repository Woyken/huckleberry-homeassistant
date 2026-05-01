"""Potty-related sensors for Huckleberry."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_datetime, as_iso8601_datetime


def build_potty_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build potty sensors."""
    return [HuckleberryPottySensor(coordinator, child) for child in children]


class HuckleberryPottySensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last potty information."""

    _attr_icon = "mdi:toilet"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "potty"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_potty"

    @property
    def native_value(self):
        """Return the last potty timestamp."""
        diaper_status = self.coordinator.get_diaper_status(self.child_uid)
        prefs = diaper_status.prefs if diaper_status is not None else None
        last_potty = prefs.lastPotty if prefs is not None else None

        return as_datetime(last_potty.start if last_potty is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return potty attributes."""
        diaper_status = self.coordinator.get_diaper_status(self.child_uid)
        prefs = diaper_status.prefs if diaper_status is not None else None
        last_potty = prefs.lastPotty if prefs is not None else None
        if last_potty is None:
            return {}

        attributes: dict[str, object] = {}
        if last_potty.start is not None:
            attributes["time"] = as_iso8601_datetime(last_potty.start)
        if last_potty.mode is not None:
            attributes["type"] = last_potty.mode.title()
        if last_potty.offset is not None:
            attributes["timezone_offset_minutes"] = last_potty.offset
        if prefs is not None and prefs.reminderV2 is not None:
            attributes["reminder"] = prefs.reminderV2.model_dump(exclude_none=True)

        return attributes

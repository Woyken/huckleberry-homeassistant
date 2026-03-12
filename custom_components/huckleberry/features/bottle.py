"""Bottle-related entities for Huckleberry."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_datetime, as_iso8601_datetime


def build_bottle_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build bottle-related sensors."""
    return [HuckleberryBottleSensor(coordinator, child) for child in children]


class HuckleberryBottleSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last bottle feeding information."""

    _attr_icon = "mdi:baby-bottle"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "bottle"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_bottle"

    def _last_bottle(self):
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        prefs = feed_status.prefs if feed_status is not None else None
        return prefs.lastBottle if prefs is not None else None

    @property
    def native_value(self):
        """Return the last bottle feeding timestamp."""
        last_bottle = self._last_bottle()
        return as_datetime(last_bottle.start if last_bottle is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return bottle feeding attributes."""
        last_bottle = self._last_bottle()
        if last_bottle is None:
            return {}

        attributes: dict[str, object] = {}
        if last_bottle.start is not None:
            attributes["time"] = as_iso8601_datetime(last_bottle.start)
        if last_bottle.bottleAmount is not None:
            attributes["amount"] = last_bottle.bottleAmount
        if last_bottle.bottleUnits is not None:
            attributes["units"] = last_bottle.bottleUnits
        if last_bottle.bottleType is not None:
            attributes["type"] = last_bottle.bottleType.title()

        return attributes

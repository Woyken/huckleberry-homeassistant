"""Solid food feeding sensors for Huckleberry."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from huckleberry_api.firebase_types import FirebaseLastSolidData

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_datetime, as_iso8601_datetime


def build_solids_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build solid food feeding sensors."""
    return [HuckleberrySolidsSensor(coordinator, child) for child in children]


class HuckleberrySolidsSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the last solid food meal."""

    _attr_icon = "mdi:food-apple"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "solids"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_solids"

    def _last_solid(self) -> FirebaseLastSolidData | None:
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        prefs = feed_status.prefs if feed_status is not None else None
        return prefs.lastSolid if prefs is not None else None

    @property
    def native_value(self) -> datetime | None:
        """Return the last solid food meal timestamp."""
        last_solid = self._last_solid()
        return as_datetime(last_solid.start if last_solid is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return solid food meal attributes."""
        last_solid = self._last_solid()
        if last_solid is None:
            return {}

        attributes: dict[str, object] = {}
        if last_solid.start is not None:
            attributes["time"] = as_iso8601_datetime(last_solid.start)
        if last_solid.foods is not None:
            attributes["foods"] = [food.created_name for food in last_solid.foods.values()]
        if last_solid.notes is not None:
            attributes["notes"] = last_solid.notes
        reaction = next((key for key, selected in (last_solid.reactions or {}).items() if selected), None)
        if reaction is not None:
            attributes["reaction"] = reaction
        return attributes

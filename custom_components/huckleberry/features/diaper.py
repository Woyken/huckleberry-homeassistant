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
    _attr_translation_key = "diaper"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
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
        """Return diaper change attributes including rich interval details."""
        diaper_status = self.coordinator.get_diaper_status(self.child_uid)
        prefs = diaper_status.prefs if diaper_status is not None else None
        last_diaper = prefs.lastDiaper if prefs is not None else None

        attributes: dict[str, object] = {}

        if last_diaper is not None:
            if last_diaper.start is not None:
                attributes["time"] = as_iso8601_datetime(last_diaper.start)
            if last_diaper.mode is not None:
                attributes["type"] = last_diaper.mode.title()

        # Enrich with detailed data from the latest interval
        latest = self.coordinator.get_latest_diaper_interval(self.child_uid)
        if latest is not None:
            amount_map = {0.0: "little", 50.0: "medium", 100.0: "big"}
            if latest.quantity is not None:
                if latest.quantity.pee is not None:
                    attributes["pee_amount"] = amount_map.get(
                        float(latest.quantity.pee), str(latest.quantity.pee)
                    )
                if latest.quantity.poo is not None:
                    attributes["poo_amount"] = amount_map.get(
                        float(latest.quantity.poo), str(latest.quantity.poo)
                    )
            if latest.color is not None:
                attributes["color"] = latest.color
            if latest.consistency is not None:
                attributes["consistency"] = latest.consistency
            if latest.diaperRash is not None:
                attributes["diaper_rash"] = latest.diaperRash
            if latest.notes is not None:
                attributes["notes"] = latest.notes

        return attributes

"""Nursing-related entities for Huckleberry."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity

from huckleberry_api import HuckleberryAPI
from huckleberry_api.firebase_types import FeedSide

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_iso8601_datetime, as_iso8601_duration

_LOGGER = logging.getLogger(__name__)

FEED_STATE_OPTIONS: Final[list[str]] = ["active", "paused", "none"]


def build_nursing_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build nursing-related sensors."""
    return [HuckleberryNursingSensor(coordinator, child) for child in children]


def build_nursing_switches(
    coordinator: HuckleberryDataUpdateCoordinator,
    api: HuckleberryAPI,
    children: list[HuckleberryChildProfile],
) -> list[SwitchEntity]:
    """Build nursing-related switches."""
    entities: list[SwitchEntity] = []
    for child in children:
        entities.append(HuckleberryNursingSwitch(coordinator, api, child, "left"))
        entities.append(HuckleberryNursingSwitch(coordinator, api, child, "right"))
    return entities


class HuckleberryNursingSensor(HuckleberryBaseEntity, SensorEntity):
    """Representation of a Huckleberry nursing sensor."""

    _attr_icon = "mdi:baby-bottle"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = FEED_STATE_OPTIONS

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Nursing"
        self._attr_unique_id = f"{self.child_uid}_nursing"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        timer = feed_status.timer if feed_status is not None else None
        if timer is None:
            return None
        if not timer.active:
            return "none"
        return "paused" if timer.paused else "active"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        if feed_status is None:
            return {}

        timer = feed_status.timer
        prefs = feed_status.prefs
        attributes: dict[str, object] = {}

        if timer is not None and timer.active:
            if timer.feedStartTime is not None:
                attributes["current_start"] = as_iso8601_datetime(timer.feedStartTime)
            if timer.leftDuration is not None:
                attributes["current_left_duration"] = as_iso8601_duration(timer.leftDuration)
            if timer.rightDuration is not None:
                attributes["current_right_duration"] = as_iso8601_duration(timer.rightDuration)
            if timer.lastSide is not None and timer.lastSide != "none":
                attributes["current_last_side"] = timer.lastSide.title()
            if timer.activeSide is not None:
                attributes["current_active_side"] = timer.activeSide.title()

        last_nursing = prefs.lastNursing if prefs is not None else None
        if last_nursing is not None:
            if last_nursing.start is not None:
                attributes["previous_start"] = as_iso8601_datetime(last_nursing.start)
            if last_nursing.duration is not None:
                attributes["previous_duration"] = as_iso8601_duration(last_nursing.duration)
            if last_nursing.leftDuration is not None:
                attributes["previous_left_duration"] = as_iso8601_duration(last_nursing.leftDuration)
            if last_nursing.rightDuration is not None:
                attributes["previous_right_duration"] = as_iso8601_duration(last_nursing.rightDuration)

        if prefs is not None and prefs.lastSide is not None:
            attributes["previous_last_side"] = prefs.lastSide.lastSide.title()

        return attributes


class HuckleberryNursingSwitch(HuckleberryBaseEntity, SwitchEntity):
    """Switch to start or stop nursing tracking for a specific side."""

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        api: HuckleberryAPI,
        child: HuckleberryChildProfile,
        side: FeedSide,
    ) -> None:
        super().__init__(coordinator, child)
        self._api = api
        self._side: FeedSide = side
        self._attr_name = f"Nursing {side}"
        self._attr_unique_id = f"{self.child_uid}_nursing_{side}"
        self._attr_icon = "mdi:baby-bottle" if side == "left" else "mdi:baby-bottle-outline"

    @property
    def is_on(self) -> bool:
        """Return true if nursing tracking is active on this side."""
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        timer = feed_status.timer if feed_status is not None else None
        if timer is None or not timer.active or timer.paused:
            return False

        active_side = timer.activeSide or timer.lastSide
        return active_side == self._side

    async def async_turn_on(self, **kwargs: object) -> None:
        """Start nursing tracking on this side."""
        _LOGGER.info("Starting %s nursing for %s", self._side, self.child_name)
        await self._api.start_nursing(self.child_uid, self._side)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Complete nursing tracking and save to history."""
        _LOGGER.info("Completing nursing for %s", self.child_name)
        await self._api.complete_nursing(self.child_uid)

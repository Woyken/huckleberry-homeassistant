"""Sleep-related entities for Huckleberry."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity

from huckleberry_api import HuckleberryAPI

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_iso8601_datetime, as_iso8601_duration

_LOGGER = logging.getLogger(__name__)

SLEEP_STATE_OPTIONS: Final[list[str]] = ["active", "paused", "none"]


def build_sleep_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build sleep sensors."""
    return [HuckleberrySleepSensor(coordinator, child) for child in children]


def build_sleep_switches(
    coordinator: HuckleberryDataUpdateCoordinator,
    api: HuckleberryAPI,
    children: list[HuckleberryChildProfile],
) -> list[SwitchEntity]:
    """Build sleep switches."""
    return [HuckleberrySleepSwitch(coordinator, api, child) for child in children]


class HuckleberrySleepSensor(HuckleberryBaseEntity, SensorEntity):
    """Representation of a Huckleberry sleep sensor."""

    _attr_icon = "mdi:sleep"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = SLEEP_STATE_OPTIONS
    _attr_translation_key = "sleep"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_sleep"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        timer = sleep_status.timer if sleep_status is not None else None
        if timer is None:
            return None
        if not timer.active:
            return "none"
        return "paused" if timer.paused else "active"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        if sleep_status is None:
            return {}

        timer = sleep_status.timer
        prefs = sleep_status.prefs
        attributes: dict[str, object] = {}

        if timer is not None:
            if timer.timerStartTime is not None:
                attributes["current_start"] = as_iso8601_datetime(timer.timerStartTime)
            if timer.timerEndTime is not None and timer.paused:
                attributes["current_end"] = as_iso8601_datetime(timer.timerEndTime)

        last_sleep = prefs.lastSleep if prefs is not None else None
        if last_sleep is not None:
            if last_sleep.start is not None:
                attributes["previous_start"] = as_iso8601_datetime(last_sleep.start)
            if last_sleep.duration is not None:
                attributes["previous_duration"] = as_iso8601_duration(last_sleep.duration)

        return attributes


class HuckleberrySleepSwitch(HuckleberryBaseEntity, SwitchEntity):
    """Switch to start or stop the sleep timer."""

    _attr_translation_key = "sleep_timer"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        api: HuckleberryAPI,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._api = api
        self._attr_unique_id = f"{self.child_uid}_sleep_timer"
        self._attr_icon = "mdi:sleep"

    @property
    def is_on(self) -> bool:
        """Return true if the sleep timer is active and not paused."""
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        timer = sleep_status.timer if sleep_status is not None else None
        return bool(timer is not None and timer.active and not timer.paused)

    async def async_turn_on(self, **kwargs: object) -> None:
        """Start the sleep timer."""
        _LOGGER.info("Starting sleep timer for %s", self.child_name)
        await self._api.start_sleep(self.child_uid)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Complete the sleep timer."""
        _LOGGER.info("Stopping sleep timer for %s", self.child_name)
        await self._api.complete_sleep(self.child_uid)

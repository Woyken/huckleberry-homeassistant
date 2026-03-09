"""Switch platform for Huckleberry integration."""
from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from huckleberry_api import HuckleberryAPI

from . import HuckleberryDataUpdateCoordinator, HuckleberryEntryData
from .const import DOMAIN
from .entity import HuckleberryBaseEntity
from .models import HuckleberryChildProfile

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Huckleberry switches."""
    entry_data = cast(HuckleberryEntryData, hass.data[DOMAIN][entry.entry_id])
    entities: list[SwitchEntity] = []

    for child in entry_data["children"]:
        entities.append(HuckleberrySleepSwitch(entry_data["coordinator"], entry_data["api"], child))
        entities.append(HuckleberryFeedingSwitch(entry_data["coordinator"], entry_data["api"], child, "left"))
        entities.append(HuckleberryFeedingSwitch(entry_data["coordinator"], entry_data["api"], child, "right"))

    async_add_entities(entities)


class HuckleberrySleepSwitch(HuckleberryBaseEntity, SwitchEntity):
    """Switch to start or stop sleep tracking."""

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        api: HuckleberryAPI,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._api = api
        self._attr_name = "Sleep tracking"
        self._attr_unique_id = f"{self.child_uid}_sleep_tracking"
        self._attr_icon = "mdi:sleep"

    @property
    def is_on(self) -> bool:
        """Return true if sleep tracking is active and not paused."""
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        timer = sleep_status.timer if sleep_status is not None else None
        return bool(timer is not None and timer.active and not timer.paused)

    async def async_turn_on(self, **kwargs: object) -> None:
        """Start sleep tracking."""
        _LOGGER.info("Starting sleep tracking for %s", self.child_name)
        await self._api.start_sleep(self.child_uid)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Complete sleep tracking."""
        _LOGGER.info("Stopping sleep tracking for %s", self.child_name)
        await self._api.complete_sleep(self.child_uid)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra state attributes."""
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        if sleep_status is None:
            return {}

        timer = sleep_status.timer
        prefs = sleep_status.prefs
        attributes: dict[str, object] = {}

        if timer is not None and self.is_on and timer.timestamp is not None:
            attributes["start_time"] = timer.timestamp.seconds

        last_sleep = prefs.lastSleep if prefs is not None else None
        if last_sleep is not None:
            if last_sleep.duration is not None:
                attributes["last_sleep_duration_minutes"] = round(float(last_sleep.duration) / 60, 1)
            if last_sleep.start is not None:
                attributes["last_sleep_start"] = last_sleep.start

        return attributes


class HuckleberryFeedingSwitch(HuckleberryBaseEntity, SwitchEntity):
    """Switch to start or stop nursing tracking for a specific side."""

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        api: HuckleberryAPI,
        child: HuckleberryChildProfile,
        side: str,
    ) -> None:
        super().__init__(coordinator, child)
        self._api = api
        self._side = side
        self._attr_name = f"Feeding {side}"
        self._attr_unique_id = f"{self.child_uid}_feeding_{side}"
        self._attr_icon = "mdi:baby-bottle" if side == "left" else "mdi:baby-bottle-outline"

    @property
    def is_on(self) -> bool:
        """Return true if feeding tracking is active on this side."""
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        timer = feed_status.timer if feed_status is not None else None
        if timer is None or not timer.active or timer.paused:
            return False

        active_side = timer.activeSide or timer.lastSide
        return active_side == self._side

    async def async_turn_on(self, **kwargs: object) -> None:
        """Start feeding tracking on this side."""
        _LOGGER.info("Starting %s nursing for %s", self._side, self.child_name)
        await self._api.start_nursing(self.child_uid, self._side)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Complete feeding tracking and save to history."""
        _LOGGER.info("Completing nursing for %s", self.child_name)
        await self._api.complete_nursing(self.child_uid)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra state attributes."""
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        if feed_status is None:
            return {}

        timer = feed_status.timer
        prefs = feed_status.prefs
        attributes: dict[str, object] = {"side": self._side}

        if timer is not None and self.is_on:
            if timer.timestamp is not None:
                attributes["feeding_start"] = timer.timestamp.seconds
            if self._side == "left" and timer.leftDuration is not None:
                attributes["duration_seconds"] = timer.leftDuration
            if self._side == "right" and timer.rightDuration is not None:
                attributes["duration_seconds"] = timer.rightDuration

        last_nursing = prefs.lastNursing if prefs is not None else None
        if last_nursing is not None:
            if last_nursing.leftDuration is not None:
                attributes["last_nursing_left_duration"] = last_nursing.leftDuration
            if last_nursing.rightDuration is not None:
                attributes["last_nursing_right_duration"] = last_nursing.rightDuration
            if last_nursing.start is not None:
                attributes["last_nursing_timestamp"] = last_nursing.start

        return attributes

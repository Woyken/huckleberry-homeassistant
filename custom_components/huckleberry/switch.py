"""Switch platform for Huckleberry integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HuckleberryBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Huckleberry switch based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    children = data["children"]

    entities = []
    for child in children:
        entities.append(HuckleberrySleepSwitch(coordinator, api, child))
        entities.append(HuckleberryFeedingSwitch(coordinator, api, child, "left"))
        entities.append(HuckleberryFeedingSwitch(coordinator, api, child, "right"))

    async_add_entities(entities)


class HuckleberrySleepSwitch(HuckleberryBaseEntity, SwitchEntity):  # pylint: disable=abstract-method
    """Switch to start/stop sleep tracking."""

    def __init__(self, coordinator, api, child: dict) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, child)
        self._api = api
        self._attr_name = "Sleep tracking"
        self._attr_unique_id = f"{self.child_uid}_sleep_tracking"
        self._attr_icon = "mdi:sleep"

    @property
    def is_on(self) -> bool:
        """Return true if sleep tracking is active."""
        if self.available:
            sleep_status = self.coordinator.data[self.child_uid].get("sleep_status", {})
            timer = sleep_status.get("timer", {})
            return timer.get("active", False) and not timer.get("paused", False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start sleep tracking."""
        _LOGGER.info("Starting sleep tracking for %s", self.child_name)
        try:
            await self._api.start_sleep(self.child_uid)
            # Real-time listener will update state automatically
        except Exception as err:
            _LOGGER.error("Failed to start sleep tracking: %s", err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop sleep tracking."""
        _LOGGER.info("Stopping sleep tracking for %s", self.child_name)
        try:
            await self._api.complete_sleep(self.child_uid)
            # Real-time listener will update state automatically
        except Exception as err:
            _LOGGER.error("Failed to stop sleep tracking: %s", err)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.available:
            return {}

        sleep_status = self.coordinator.data[self.child_uid].get("sleep_status", {})
        timer = sleep_status.get("timer", {})

        attrs = {}

        if self.is_on and "timestamp" in timer:
            attrs["start_time"] = timer["timestamp"].get("seconds")

        # Add last sleep info
        prefs = sleep_status.get("prefs", {})
        if "lastSleep" in prefs:
            last_sleep = prefs["lastSleep"]
            attrs["last_sleep_duration_minutes"] = round(last_sleep.get("duration", 0) / 60, 1)
            attrs["last_sleep_start"] = last_sleep.get("start")

        return attrs


class HuckleberryFeedingSwitch(HuckleberryBaseEntity, SwitchEntity):  # pylint: disable=abstract-method
    """Switch to start/stop breast feeding tracking for specific side."""

    def __init__(self, coordinator, api, child: dict, side: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, child)
        self._api = api
        self._side = side
        self._attr_name = f"Feeding {side}"
        self._attr_unique_id = f"{self.child_uid}_feeding_{side}"
        self._attr_icon = "mdi:baby-bottle" if side == "left" else "mdi:baby-bottle-outline"

    @property
    def is_on(self) -> bool:
        """Return true if feeding tracking is active on this side."""
        if self.available:
            feed_status = self.coordinator.data[self.child_uid].get("feed_status", {})
            timer = feed_status.get("timer", {})

            # Active if timer is active and activeSide matches this switch's side
            is_active = timer.get("active", False) and not timer.get("paused", False)
            active_side = timer.get("activeSide", timer.get("lastSide", ""))

            return is_active and active_side == self._side
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start feeding tracking on this side."""
        _LOGGER.info("Starting %s breast feeding for %s", self._side, self.child_name)
        try:
            await self._api.start_nursing(self.child_uid, self._side)
            # Real-time listener will update state automatically
        except Exception as err:
            _LOGGER.error("Failed to start feeding tracking: %s", err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Complete feeding tracking and save to history."""
        _LOGGER.info("Completing %s breast feeding for %s", self._side, self.child_name)
        try:
            await self._api.complete_nursing(self.child_uid)
            # Real-time listener will update state automatically
        except Exception as err:
            _LOGGER.error("Failed to complete feeding tracking: %s", err)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.available:
            return {}

        feed_status = self.coordinator.data[self.child_uid].get("feed_status", {})
        timer = feed_status.get("timer", {})
        prefs = feed_status.get("prefs", {})

        attrs = {
            "side": self._side,
        }

        if self.is_on:
            if "timestamp" in timer:
                attrs["feeding_start"] = timer["timestamp"].get("seconds")

            # Show duration for this side
            if self._side == "left":
                attrs["duration_seconds"] = timer.get("leftDuration", 0)
            else:
                attrs["duration_seconds"] = timer.get("rightDuration", 0)

        # Add last nursing info
        if "lastNursing" in prefs:
            last_nursing = prefs["lastNursing"]
            attrs["last_nursing_left_duration"] = last_nursing.get("leftDuration", 0)
            attrs["last_nursing_right_duration"] = last_nursing.get("rightDuration", 0)
            attrs["last_nursing_timestamp"] = last_nursing.get("timestamp")

        return attrs

"""Sensor platform for Huckleberry."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .entity import HuckleberryBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Huckleberry sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    children = data["children"]

    entities: list[SensorEntity] = [HuckleberryChildrenSensor(coordinator, children)]

    # Add individual child profile sensor for each child
    for child in children:
        entities.append(HuckleberryChildProfileSensor(coordinator, child))
        # Add growth sensor for each child
        entities.append(HuckleberryGrowthSensor(coordinator, child))
        # Add diaper sensor for each child
        entities.append(HuckleberryDiaperSensor(coordinator, child))
        # Add sleep sensor for each child
        entities.append(HuckleberrySleepSensor(coordinator, child))
        # Add feeding sensor for each child
        entities.append(HuckleberryFeedingSensor(coordinator, child))
        # Add last feeding side sensor for each child
        entities.append(HuckleberryLastFeedingSideSensor(coordinator, child))
        # Add previous sleep sensors for each child
        entities.append(HuckleberryPreviousSleepStartSensor(coordinator, child))
        entities.append(HuckleberryPreviousSleepEndSensor(coordinator, child))
        # Add previous feed sensor for each child
        entities.append(HuckleberryPreviousFeedSensor(coordinator, child))

    async_add_entities(entities)


class HuckleberryChildrenSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing children information."""

    _attr_icon = "mdi:account-child"
    _attr_native_unit_of_measurement = "children"

    def __init__(self, coordinator, children: list[dict[str, Any]]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._children = children

        self._attr_name = "Huckleberry Children"
        self._attr_unique_id = "huckleberry_children"

    @property
    def native_value(self) -> int:
        """Return the count of children."""
        return len(self._children)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "children": [
                {
                    "uid": child["uid"],
                    "name": child["name"],
                    "birthday": child.get("birthday"),
                    "picture": child.get("picture"),
                    "gender": child.get("gender"),
                    "color": child.get("color"),
                    "created_at": child.get("created_at"),
                    "night_start": child.get("night_start"),
                    "morning_cutoff": child.get("morning_cutoff"),
                    "expected_naps": child.get("expected_naps"),
                    "categories": child.get("categories"),
                }
                for child in self._children
            ],
            "child_ids": [child["uid"] for child in self._children],
            "child_names": [child["name"] for child in self._children],
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success


class HuckleberryChildProfileSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing individual child profile information."""

    _attr_icon = "mdi:account"

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Profile"
        self._attr_unique_id = f"{self.child_uid}_profile"

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use in the frontend."""
        return self._child.get("picture")

    @property
    def native_value(self) -> str:
        """Return the child's name as the state."""
        return self.child_name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return child profile attributes."""
        attrs = {
            "uid": self.child_uid,
            "name": self.child_name,
        }

        # Add all available child attributes
        optional_fields = [
            "birthday", "picture", "gender", "color", "created_at",
            "night_start", "morning_cutoff", "expected_naps", "categories"
        ]
        for field in optional_fields:
            if self._child.get(field) is not None:
                attrs[field] = self._child[field]

        return attrs


class HuckleberryGrowthSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing child growth measurements."""

    _attr_icon = "mdi:human-male-height"

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Growth"
        self._attr_unique_id = f"{self.child_uid}_growth"

    @property
    def native_value(self) -> str | None:
        """Return the most recent measurement timestamp."""
        child_data = self.coordinator.data.get(self.child_uid, {})
        growth_data = child_data.get("growth_data", {})

        if not growth_data:
            return "No data"

        timestamp = growth_data.get("timestamp")
        if timestamp:
            from datetime import datetime
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return growth measurement attributes."""
        child_data = self.coordinator.data.get(self.child_uid, {})
        growth_data = child_data.get("growth_data", {})

        if not growth_data:
            return {}

        attrs = {}

        # Add measurements if available
        weight = growth_data.get("weight")
        height = growth_data.get("height")
        head = growth_data.get("head")

        if weight is not None:
            weight_unit = growth_data.get("weight_units", "kg")
            attrs["weight"] = weight
            attrs["weight_unit"] = weight_unit
            attrs["weight_display"] = f"{weight} {weight_unit}"

        if height is not None:
            height_unit = growth_data.get("height_units", "cm")
            attrs["height"] = height
            attrs["height_unit"] = height_unit
            attrs["height_display"] = f"{height} {height_unit}"

        if head is not None:
            head_unit = growth_data.get("head_units", "hcm")
            attrs["head_circumference"] = head
            attrs["head_unit"] = head_unit
            attrs["head_display"] = f"{head} {head_unit}"

        timestamp = growth_data.get("timestamp")
        if timestamp:
            from datetime import datetime
            attrs["last_measured"] = datetime.fromtimestamp(timestamp).isoformat()

        return attrs


class HuckleberryDiaperSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last diaper change information."""

    _attr_icon = "mdi:baby"

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Last Diaper"
        self._attr_unique_id = f"{self.child_uid}_last_diaper"

    @property
    def native_value(self) -> str | None:
        """Return the last diaper change timestamp."""
        child_data = self.coordinator.data.get(self.child_uid, {})
        diaper_data = child_data.get("diaper_data", {})

        prefs = diaper_data.get("prefs", {})
        last_diaper = prefs.get("lastDiaper", {})

        if not last_diaper:
            return "No changes logged"

        timestamp = last_diaper.get("start")
        if timestamp:
            from datetime import datetime
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diaper change attributes."""
        child_data = self.coordinator.data.get(self.child_uid, {})
        diaper_data = child_data.get("diaper_data", {})

        prefs = diaper_data.get("prefs", {})
        last_diaper = prefs.get("lastDiaper", {})

        if not last_diaper:
            return {}

        attrs = {}

        # Add timestamp
        timestamp = last_diaper.get("start")
        if timestamp:
            from datetime import datetime
            attrs["timestamp"] = timestamp
            attrs["time"] = datetime.fromtimestamp(timestamp).isoformat()

        # Add mode (pee, poo, both, dry)
        mode = last_diaper.get("mode")
        if mode:
            attrs["mode"] = mode
            attrs["type"] = mode.capitalize()

        # Add offset (timezone)
        offset = last_diaper.get("offset")
        if offset is not None:
            attrs["timezone_offset_minutes"] = offset

        return attrs


class HuckleberrySleepSensor(HuckleberryBaseEntity, SensorEntity):
    """Representation of a Huckleberry sleep sensor."""

    _attr_icon = "mdi:sleep"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["sleeping", "paused", "none"]

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Sleep status"
        self._attr_unique_id = f"{self.child_uid}_sleep_status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.child_uid not in self.coordinator.data:
            return "none"

        sleep_status = self.coordinator.data[self.child_uid].get("sleep_status", {})

        # Check real-time timer data structure
        if isinstance(sleep_status, dict) and "timer" in sleep_status:
            timer = sleep_status.get("timer", {})
            if timer.get("active"):
                if timer.get("paused"):
                    return "paused"
                return "sleeping"

        return "none"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if self.child_uid not in self.coordinator.data:
            return {}

        sleep_status = self.coordinator.data[self.child_uid].get("sleep_status", {})

        attrs = {}

        # Handle real-time data structure
        if isinstance(sleep_status, dict) and "timer" in sleep_status:
            timer = sleep_status.get("timer", {})
            prefs = sleep_status.get("prefs", {})

            # Track paused state
            if timer.get("active"):
                attrs["is_paused"] = timer.get("paused", False)

                # timerStartTime is in milliseconds for sleep tracking
                if "timerStartTime" in timer:
                    attrs["timer_start_time_ms"] = timer.get("timerStartTime")
                    # Convert to seconds for chronometer (Home Assistant expects Unix timestamp)
                    attrs["timer_start_time"] = int(timer.get("timerStartTime") / 1000)

            if timer.get("active") and not timer.get("paused"):
                # Currently sleeping
                if "timestamp" in timer:
                    attrs["sleep_start"] = timer["timestamp"].get("seconds")

            if timer.get("paused"):
                # Sleep is currently paused
                if "timerEndTime" in timer:
                    attrs["timer_end_time_ms"] = timer.get("timerEndTime")
                    attrs["timer_end_time"] = int(timer.get("timerEndTime") / 1000)

            # Last sleep info
            if "lastSleep" in prefs:
                last_sleep = prefs["lastSleep"]
                attrs["last_sleep_duration_seconds"] = last_sleep.get("duration")
                attrs["last_sleep_start"] = last_sleep.get("start")
        else:
            # Fallback to legacy computed structure
            attrs["last_updated"] = sleep_status.get("last_updated")

            duration = sleep_status.get("sleep_duration")
            start = sleep_status.get("sleep_start")
            if start:
                attrs["sleep_start"] = start
            if duration is not None:
                attrs["sleep_duration_seconds"] = duration
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                attrs["sleep_duration"] = f"{hours}h {minutes}m"

        return attrs


class HuckleberryFeedingSensor(HuckleberryBaseEntity, SensorEntity):
    """Representation of a Huckleberry feeding sensor."""

    _attr_icon = "mdi:baby-bottle"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["feeding", "paused", "none"]

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Feeding status"
        self._attr_unique_id = f"{self.child_uid}_feeding_status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.child_uid not in self.coordinator.data:
            return "none"

        feed_status = self.coordinator.data[self.child_uid].get("feed_status", {})

        # Check real-time timer data structure
        if isinstance(feed_status, dict) and "timer" in feed_status:
            timer = feed_status.get("timer", {})
            if timer.get("active"):
                if timer.get("paused"):
                    return "paused"
                return "feeding"

        return "none"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if self.child_uid not in self.coordinator.data:
            return {}

        feed_status = self.coordinator.data[self.child_uid].get("feed_status", {})

        attrs = {}

        # Handle real-time data structure
        if isinstance(feed_status, dict) and "timer" in feed_status:
            timer = feed_status.get("timer", {})
            prefs = feed_status.get("prefs", {})

            # Track paused state
            if timer.get("active"):
                attrs["is_paused"] = timer.get("paused", False)

            if timer.get("active"):
                # Currently feeding (active or paused)
                # Use feedStartTime (absolute start) not timestamp (last update)
                if "feedStartTime" in timer:
                    attrs["feeding_start"] = timer["feedStartTime"]
                attrs["left_duration_seconds"] = timer.get("leftDuration", 0)
                attrs["right_duration_seconds"] = timer.get("rightDuration", 0)
                attrs["last_side"] = timer.get("lastSide", "unknown")

            # Last feeding info
            if "lastNursing" in prefs:
                last_nursing = prefs["lastNursing"]
                attrs["last_nursing_start"] = last_nursing.get("start")
                attrs["last_nursing_duration_seconds"] = last_nursing.get("duration")
                attrs["last_nursing_left_seconds"] = last_nursing.get("leftDuration", 0)
                attrs["last_nursing_right_seconds"] = last_nursing.get("rightDuration", 0)

        return attrs


class HuckleberryLastFeedingSideSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the last feeding side."""

    _attr_icon = "mdi:baby-bottle-outline"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["Left", "Right", "Unknown"]

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Last Feeding Side"
        self._attr_unique_id = f"{self.child_uid}_last_feeding_side"

    @property
    def native_value(self) -> str:
        """Return the last feeding side."""
        if self.child_uid not in self.coordinator.data:
            return "Unknown"

        feed_status = self.coordinator.data[self.child_uid].get("feed_status", {})
        if not isinstance(feed_status, dict):
            return "Unknown"

        timer = feed_status.get("timer", {})
        prefs = feed_status.get("prefs", {})

        # If currently feeding (active)
        if timer.get("active"):
            # If activeSide is present (feeding), use it
            active_side = timer.get("activeSide")
            if active_side and active_side != "none":
                return active_side.title()

            # If paused, activeSide is removed, use lastSide from timer
            # Note: pause_feeding sets timer.lastSide = current_side
            last_side = timer.get("lastSide")
            if last_side and last_side != "none":
                return last_side.title()

        # If not active, or fallback
        # Check prefs.lastSide (history)
        last_side_pref = prefs.get("lastSide", {})
        if last_side_pref and "lastSide" in last_side_pref:
            side = last_side_pref["lastSide"]
            if side and side != "none":
                return side.title()

        # Fallback to timer.lastSide if prefs missing
        last_side = timer.get("lastSide")
        if last_side and last_side != "none":
            return last_side.title()

        return "Unknown"

class HuckleberryPreviousSleepStartSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the start time of the previous sleep session."""

    _attr_icon = "mdi:sleep"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Previous Sleep Start"
        self._attr_unique_id = f"{self.child_uid}_previous_sleep_start"

    @property
    def native_value(self):
        """Return the start time of the last sleep."""
        if self.child_uid not in self.coordinator.data:
            return None

        sleep_status = self.coordinator.data[self.child_uid].get("sleep_status", {})
        if not isinstance(sleep_status, dict):
            return None

        prefs = sleep_status.get("prefs", {})
        last_sleep = prefs.get("lastSleep", {})

        start = last_sleep.get("start")

        if start is not None:
            from datetime import datetime, timezone
            return datetime.fromtimestamp(start, tz=timezone.utc)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if self.child_uid not in self.coordinator.data:
            return {}

        sleep_status = self.coordinator.data[self.child_uid].get("sleep_status", {})
        if not isinstance(sleep_status, dict):
            return {}

        prefs = sleep_status.get("prefs", {})
        last_sleep = prefs.get("lastSleep", {})

        attrs = {}
        duration = last_sleep.get("duration")
        if duration is not None:
            attrs["duration_seconds"] = duration
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            attrs["duration"] = f"{hours}h {minutes}m"

        return attrs

class HuckleberryPreviousSleepEndSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the end time of the previous sleep session."""

    _attr_icon = "mdi:sleep-off"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Previous Sleep End"
        self._attr_unique_id = f"{self.child_uid}_previous_sleep_end"

    @property
    def native_value(self):
        """Return the end time of the last sleep."""
        if self.child_uid not in self.coordinator.data:
            return None

        sleep_status = self.coordinator.data[self.child_uid].get("sleep_status", {})
        if not isinstance(sleep_status, dict):
            return None

        prefs = sleep_status.get("prefs", {})
        last_sleep = prefs.get("lastSleep", {})

        start = last_sleep.get("start")
        duration = last_sleep.get("duration")

        if start is not None and duration is not None:
            from datetime import datetime, timezone
            # Timestamps are in seconds
            end_timestamp = start + duration
            return datetime.fromtimestamp(end_timestamp, tz=timezone.utc)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if self.child_uid not in self.coordinator.data:
            return {}

        sleep_status = self.coordinator.data[self.child_uid].get("sleep_status", {})
        if not isinstance(sleep_status, dict):
            return {}

        prefs = sleep_status.get("prefs", {})
        last_sleep = prefs.get("lastSleep", {})

        attrs = {}
        duration = last_sleep.get("duration")
        if duration is not None:
            attrs["duration_seconds"] = duration
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            attrs["duration"] = f"{hours}h {minutes}m"

        return attrs


class HuckleberryPreviousFeedSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the start time of the previous feeding session."""

    _attr_icon = "mdi:baby-bottle-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, child)
        self._attr_name = "Previous Feed Start"
        self._attr_unique_id = f"{self.child_uid}_previous_feed_start"

    @property
    def native_value(self):
        """Return the start time of the last feeding."""
        if self.child_uid not in self.coordinator.data:
            return None

        feed_status = self.coordinator.data[self.child_uid].get("feed_status", {})
        if not isinstance(feed_status, dict):
            return None

        prefs = feed_status.get("prefs", {})
        last_nursing = prefs.get("lastNursing", {})

        start = last_nursing.get("start")

        if start is not None:
            from datetime import datetime, timezone
            return datetime.fromtimestamp(start, tz=timezone.utc)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if self.child_uid not in self.coordinator.data:
            return {}

        feed_status = self.coordinator.data[self.child_uid].get("feed_status", {})
        if not isinstance(feed_status, dict):
            return {}

        prefs = feed_status.get("prefs", {})
        last_nursing = prefs.get("lastNursing", {})
        last_side_data = prefs.get("lastSide", {})

        attrs = {}

        duration = last_nursing.get("duration")
        if duration is not None:
            attrs["duration_seconds"] = duration

        left_duration = last_nursing.get("leftDuration")
        if left_duration is not None:
            attrs["left_duration_seconds"] = left_duration

        right_duration = last_nursing.get("rightDuration")
        if right_duration is not None:
            attrs["right_duration_seconds"] = right_duration

        last_side = last_side_data.get("lastSide")
        if last_side:
            attrs["last_side"] = last_side

        return attrs



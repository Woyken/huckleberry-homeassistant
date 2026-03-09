"""Sensor platform for Huckleberry."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Final, cast

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from huckleberry_api.firebase_types import FirebaseLastBottleData, FirebaseLastNursingData, FirebaseLastSleepData

from . import HuckleberryDataUpdateCoordinator, HuckleberryEntryData
from .const import DOMAIN
from .entity import HuckleberryBaseEntity
from .models import HuckleberryChildProfile, children_sensor_attributes

SLEEP_STATE_OPTIONS: Final[list[str]] = ["sleeping", "paused", "none"]
FEED_STATE_OPTIONS: Final[list[str]] = ["feeding", "paused", "none"]
LAST_SIDE_OPTIONS: Final[list[str]] = ["Left", "Right", "Unknown"]


def _as_local_timestamp(value: int | float | None) -> str | None:
    """Format a unix timestamp as local text for string sensors."""
    if value is None:
        return None
    return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M")


def _as_datetime(value: int | float | None) -> datetime | None:
    """Convert a unix timestamp to a UTC datetime for timestamp sensors."""
    if value is None:
        return None
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def _duration_text(value: int | float | None) -> str | None:
    """Return a simple hours/minutes duration string."""
    if value is None:
        return None
    total_seconds = int(float(value))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Huckleberry sensors."""
    entry_data = cast(HuckleberryEntryData, hass.data[DOMAIN][entry.entry_id])
    coordinator = entry_data["coordinator"]
    children = entry_data["children"]

    entities: list[SensorEntity] = [HuckleberryChildrenSensor(coordinator, children)]
    for child in children:
        entities.append(HuckleberryChildProfileSensor(coordinator, child))
        entities.append(HuckleberryGrowthSensor(coordinator, child))
        entities.append(HuckleberryDiaperSensor(coordinator, child))
        entities.append(HuckleberryBottleSensor(coordinator, child))
        entities.append(HuckleberrySleepSensor(coordinator, child))
        entities.append(HuckleberryFeedingSensor(coordinator, child))
        entities.append(HuckleberryLastFeedingSideSensor(coordinator, child))
        entities.append(HuckleberryPreviousSleepStartSensor(coordinator, child))
        entities.append(HuckleberryPreviousSleepEndSensor(coordinator, child))
        entities.append(HuckleberryPreviousFeedSensor(coordinator, child))

    async_add_entities(entities)


class HuckleberryChildrenSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing children information."""

    _attr_icon = "mdi:account-child"
    _attr_native_unit_of_measurement = "children"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        children: list[HuckleberryChildProfile],
    ) -> None:
        super().__init__(coordinator)
        self._children = children
        self._attr_name = "Huckleberry Children"
        self._attr_unique_id = "huckleberry_children"

    @property
    def native_value(self) -> int:
        """Return the count of children."""
        return len(self._children)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        return children_sensor_attributes(self._children)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success


class HuckleberryChildProfileSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing individual child profile information."""

    _attr_icon = "mdi:account"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Profile"
        self._attr_unique_id = f"{self.child_uid}_profile"

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use in the frontend."""
        return self._child.picture

    @property
    def native_value(self) -> str:
        """Return the child's name as the state."""
        return self.child_name

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return child profile attributes."""
        return self._child.as_attributes()


class HuckleberryGrowthSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing child growth measurements."""

    _attr_icon = "mdi:human-male-height"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Growth"
        self._attr_unique_id = f"{self.child_uid}_growth"

    @property
    def native_value(self) -> str:
        """Return the most recent measurement timestamp."""
        state = self.coordinator.get_state(self.child_uid)
        growth_data = state.growth_data if state is not None else None
        if growth_data is None:
            return "No data"
        return _as_local_timestamp(growth_data.start) or "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return growth measurement attributes."""
        state = self.coordinator.get_state(self.child_uid)
        growth_data = state.growth_data if state is not None else None
        if growth_data is None:
            return {}

        attributes: dict[str, object] = {}
        if growth_data.weight is not None:
            attributes["weight"] = growth_data.weight
            attributes["weight_unit"] = growth_data.weightUnits
            attributes["weight_display"] = f"{growth_data.weight} {growth_data.weightUnits}"
        if growth_data.height is not None:
            attributes["height"] = growth_data.height
            attributes["height_unit"] = growth_data.heightUnits
            attributes["height_display"] = f"{growth_data.height} {growth_data.heightUnits}"
        if growth_data.head is not None:
            attributes["head_circumference"] = growth_data.head
            attributes["head_unit"] = growth_data.headUnits
            attributes["head_display"] = f"{growth_data.head} {growth_data.headUnits}"
        if growth_data.start is not None:
            measured = _as_datetime(growth_data.start)
            if measured is not None:
                attributes["last_measured"] = measured.isoformat()
        return attributes


class HuckleberryDiaperSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last diaper change information."""

    _attr_icon = "mdi:baby"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Last Diaper"
        self._attr_unique_id = f"{self.child_uid}_last_diaper"

    @property
    def native_value(self) -> str:
        """Return the last diaper change timestamp."""
        diaper_status = self.coordinator.get_diaper_status(self.child_uid)
        prefs = diaper_status.prefs if diaper_status is not None else None
        last_diaper = prefs.lastDiaper if prefs is not None else None
        if last_diaper is None or last_diaper.start is None:
            return "No changes logged"
        return _as_local_timestamp(last_diaper.start) or "Unknown"

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
            attributes["timestamp"] = last_diaper.start
            time_value = _as_datetime(last_diaper.start)
            if time_value is not None:
                attributes["time"] = time_value.isoformat()
        if last_diaper.mode is not None:
            attributes["mode"] = last_diaper.mode
            attributes["type"] = last_diaper.mode.capitalize()
        if last_diaper.offset is not None:
            attributes["timezone_offset_minutes"] = last_diaper.offset
        return attributes


class HuckleberryBottleSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last bottle feeding information."""

    _attr_icon = "mdi:baby-bottle"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Last Bottle"
        self._attr_unique_id = f"{self.child_uid}_last_bottle"

    def _last_bottle(self) -> FirebaseLastBottleData | None:
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        prefs = feed_status.prefs if feed_status is not None else None
        return prefs.lastBottle if prefs is not None else None

    @property
    def native_value(self) -> datetime | None:
        """Return the last bottle feeding timestamp."""
        last_bottle = self._last_bottle()
        return _as_datetime(last_bottle.start if last_bottle is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return bottle feeding attributes."""
        last_bottle = self._last_bottle()
        if last_bottle is None:
            return {}

        attributes: dict[str, object] = {}
        if last_bottle.start is not None:
            attributes["timestamp"] = last_bottle.start
            time_value = _as_datetime(last_bottle.start)
            if time_value is not None:
                attributes["time"] = time_value.isoformat()
        if last_bottle.bottleAmount is not None:
            attributes["amount"] = last_bottle.bottleAmount
        if last_bottle.bottleUnits is not None:
            attributes["units"] = last_bottle.bottleUnits
        if last_bottle.bottleAmount is not None and last_bottle.bottleUnits is not None:
            attributes["amount_display"] = f"{last_bottle.bottleAmount} {last_bottle.bottleUnits}"
        if last_bottle.bottleType is not None:
            attributes["bottle_type"] = last_bottle.bottleType
            attributes["type"] = last_bottle.bottleType
        if last_bottle.offset is not None:
            attributes["timezone_offset_minutes"] = last_bottle.offset
        return attributes


class HuckleberrySleepSensor(HuckleberryBaseEntity, SensorEntity):
    """Representation of a Huckleberry sleep sensor."""

    _attr_icon = "mdi:sleep"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = SLEEP_STATE_OPTIONS

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Sleep status"
        self._attr_unique_id = f"{self.child_uid}_sleep_status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        timer = sleep_status.timer if sleep_status is not None else None
        if timer is None or not timer.active:
            return "none"
        return "paused" if timer.paused else "sleeping"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        if sleep_status is None:
            return {}

        timer = sleep_status.timer
        prefs = sleep_status.prefs
        attributes: dict[str, object] = {}

        if timer is not None and timer.active:
            attributes["is_paused"] = timer.paused
            if timer.timerStartTime is not None:
                attributes["timer_start_time_ms"] = timer.timerStartTime
                attributes["timer_start_time"] = int(float(timer.timerStartTime) / 1000)
            if not timer.paused and timer.timestamp is not None:
                attributes["sleep_start"] = timer.timestamp.seconds
            if timer.paused and timer.timerEndTime is not None:
                attributes["timer_end_time_ms"] = timer.timerEndTime
                attributes["timer_end_time"] = int(float(timer.timerEndTime) / 1000)

        last_sleep = prefs.lastSleep if prefs is not None else None
        if last_sleep is not None:
            if last_sleep.duration is not None:
                attributes["last_sleep_duration_seconds"] = last_sleep.duration
            if last_sleep.start is not None:
                attributes["last_sleep_start"] = last_sleep.start

        return attributes


class HuckleberryFeedingSensor(HuckleberryBaseEntity, SensorEntity):
    """Representation of a Huckleberry feeding sensor."""

    _attr_icon = "mdi:baby-bottle"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = FEED_STATE_OPTIONS

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Feeding status"
        self._attr_unique_id = f"{self.child_uid}_feeding_status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        timer = feed_status.timer if feed_status is not None else None
        if timer is None or not timer.active:
            return "none"
        return "paused" if timer.paused else "feeding"

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
            attributes["is_paused"] = timer.paused
            if timer.feedStartTime is not None:
                attributes["feeding_start"] = timer.feedStartTime
            if timer.leftDuration is not None:
                attributes["left_duration_seconds"] = timer.leftDuration
            if timer.rightDuration is not None:
                attributes["right_duration_seconds"] = timer.rightDuration
            if timer.lastSide is not None:
                attributes["last_side"] = timer.lastSide

        last_nursing = prefs.lastNursing if prefs is not None else None
        if last_nursing is not None:
            if last_nursing.start is not None:
                attributes["last_nursing_start"] = last_nursing.start
            if last_nursing.duration is not None:
                attributes["last_nursing_duration_seconds"] = last_nursing.duration
            if last_nursing.leftDuration is not None:
                attributes["last_nursing_left_seconds"] = last_nursing.leftDuration
            if last_nursing.rightDuration is not None:
                attributes["last_nursing_right_seconds"] = last_nursing.rightDuration

        return attributes


class HuckleberryLastFeedingSideSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the last feeding side."""

    _attr_icon = "mdi:baby-bottle-outline"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = LAST_SIDE_OPTIONS

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Last Feeding Side"
        self._attr_unique_id = f"{self.child_uid}_last_feeding_side"

    @property
    def native_value(self) -> str:
        """Return the last feeding side."""
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        if feed_status is None:
            return "Unknown"

        timer = feed_status.timer
        prefs = feed_status.prefs

        if timer is not None and timer.active:
            active_side = timer.activeSide
            if active_side is not None and active_side != "none":
                return active_side.title()
            if timer.lastSide is not None and timer.lastSide != "none":
                return timer.lastSide.title()

        last_side = prefs.lastSide if prefs is not None else None
        if last_side is not None and last_side.lastSide is not None and last_side.lastSide != "none":
            return last_side.lastSide.title()

        if timer is not None and timer.lastSide is not None and timer.lastSide != "none":
            return timer.lastSide.title()

        return "Unknown"


class HuckleberryPreviousSleepStartSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the start time of the previous sleep session."""

    _attr_icon = "mdi:sleep"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Previous Sleep Start"
        self._attr_unique_id = f"{self.child_uid}_previous_sleep_start"

    def _last_sleep(self) -> FirebaseLastSleepData | None:
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        prefs = sleep_status.prefs if sleep_status is not None else None
        return prefs.lastSleep if prefs is not None else None

    @property
    def native_value(self) -> datetime | None:
        """Return the start time of the last sleep."""
        last_sleep = self._last_sleep()
        return _as_datetime(last_sleep.start if last_sleep is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        last_sleep = self._last_sleep()
        if last_sleep is None:
            return {}

        attributes: dict[str, object] = {}
        if last_sleep.duration is not None:
            attributes["duration_seconds"] = last_sleep.duration
            duration = _duration_text(last_sleep.duration)
            if duration is not None:
                attributes["duration"] = duration
        return attributes


class HuckleberryPreviousSleepEndSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the end time of the previous sleep session."""

    _attr_icon = "mdi:sleep-off"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Previous Sleep End"
        self._attr_unique_id = f"{self.child_uid}_previous_sleep_end"

    def _last_sleep(self) -> FirebaseLastSleepData | None:
        sleep_status = self.coordinator.get_sleep_status(self.child_uid)
        prefs = sleep_status.prefs if sleep_status is not None else None
        return prefs.lastSleep if prefs is not None else None

    @property
    def native_value(self) -> datetime | None:
        """Return the end time of the last sleep."""
        last_sleep = self._last_sleep()
        if last_sleep is None or last_sleep.start is None or last_sleep.duration is None:
            return None
        return _as_datetime(float(last_sleep.start) + float(last_sleep.duration))

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        last_sleep = self._last_sleep()
        if last_sleep is None:
            return {}

        attributes: dict[str, object] = {}
        if last_sleep.duration is not None:
            attributes["duration_seconds"] = last_sleep.duration
            duration = _duration_text(last_sleep.duration)
            if duration is not None:
                attributes["duration"] = duration
        return attributes


class HuckleberryPreviousFeedSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the start time of the previous feeding session."""

    _attr_icon = "mdi:baby-bottle-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Previous Feed Start"
        self._attr_unique_id = f"{self.child_uid}_previous_feed_start"

    def _last_nursing(self) -> FirebaseLastNursingData | None:
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        prefs = feed_status.prefs if feed_status is not None else None
        return prefs.lastNursing if prefs is not None else None

    @property
    def native_value(self) -> datetime | None:
        """Return the start time of the last feeding."""
        last_nursing = self._last_nursing()
        return _as_datetime(last_nursing.start if last_nursing is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        feed_status = self.coordinator.get_feed_status(self.child_uid)
        if feed_status is None:
            return {}

        last_nursing = self._last_nursing()
        last_side = feed_status.prefs.lastSide if feed_status.prefs is not None else None
        if last_nursing is None:
            return {}

        attributes: dict[str, object] = {}
        if last_nursing.duration is not None:
            attributes["duration_seconds"] = last_nursing.duration
        if last_nursing.leftDuration is not None:
            attributes["left_duration_seconds"] = last_nursing.leftDuration
        if last_nursing.rightDuration is not None:
            attributes["right_duration_seconds"] = last_nursing.rightDuration
        if last_side is not None and last_side.lastSide is not None:
            attributes["last_side"] = last_side.lastSide
        return attributes

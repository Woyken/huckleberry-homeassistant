"""Sensor platform for Huckleberry."""
from __future__ import annotations

from typing import Final, cast

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HuckleberryDataUpdateCoordinator, HuckleberryEntryData
from .const import DOMAIN
from .entity import HuckleberryBaseEntity
from .models import HuckleberryChildProfile, children_sensor_attributes
from .timestamps import as_datetime, as_iso8601_datetime, as_iso8601_duration

SLEEP_STATE_OPTIONS: Final[list[str]] = ["active", "paused", "none"]
FEED_STATE_OPTIONS: Final[list[str]] = ["active", "paused", "none"]


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
        entities.append(HuckleberryNursingSensor(coordinator, child))

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
    def native_value(self):
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
    def native_value(self):
        """Return the child's name as the state."""
        return self.child_name

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return child profile attributes."""
        return self._child.as_attributes()


class HuckleberryGrowthSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing child growth measurements."""

    _attr_icon = "mdi:human-male-height"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Growth"
        self._attr_unique_id = f"{self.child_uid}_growth"

    @property
    def native_value(self):
        """Return the most recent measurement timestamp."""
        state = self.coordinator.get_state(self.child_uid)
        growth_data = state.growth_data if state is not None else None

        return as_datetime(growth_data.start if growth_data is not None else None)

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
        if growth_data.height is not None:
            attributes["height"] = growth_data.height
            attributes["height_unit"] = growth_data.heightUnits
        if growth_data.head is not None:
            attributes["head_circumference"] = growth_data.head
            attributes["head_unit"] = growth_data.headUnits

        return attributes


class HuckleberryDiaperSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last diaper change information."""

    _attr_icon = "mdi:baby"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Diaper"
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
        """Return diaper change attributes."""
        diaper_status = self.coordinator.get_diaper_status(self.child_uid)
        prefs = diaper_status.prefs if diaper_status is not None else None
        last_diaper = prefs.lastDiaper if prefs is not None else None
        if last_diaper is None:
            return {}

        attributes: dict[str, object] = {}
        if last_diaper.start is not None:
            attributes["time"] = as_iso8601_datetime(last_diaper.start)
        if last_diaper.mode is not None:
            attributes["type"] = last_diaper.mode.title()
        return attributes


class HuckleberryBottleSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing last bottle feeding information."""

    _attr_icon = "mdi:baby-bottle"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Bottle"
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


class HuckleberrySleepSensor(HuckleberryBaseEntity, SensorEntity):
    """Representation of a Huckleberry sleep sensor."""

    _attr_icon = "mdi:sleep"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = SLEEP_STATE_OPTIONS

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Sleep"
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



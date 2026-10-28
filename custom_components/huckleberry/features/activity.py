"""Activity-related entities for Huckleberry."""
from __future__ import annotations

from datetime import datetime
from typing import Final, cast, get_args

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from huckleberry_api.firebase_types import (
    ActivityMode,
    FirebaseActivityDocumentData,
    FirebaseActivityTimerEntryData,
    FirebaseLastActivityData,
)

from .. import HuckleberryDataUpdateCoordinator
from ..const import DOMAIN
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_datetime, as_iso8601_datetime, as_iso8601_duration

ACTIVITY_MODES: Final[tuple[ActivityMode, ...]] = cast(
    tuple[ActivityMode, ...], get_args(ActivityMode)
)
ACTIVITY_LAST_FIELDS: Final[dict[ActivityMode, str]] = {
    "bath": "lastBath",
    "brushTeeth": "lastBrushTeeth",
    "indoorPlay": "lastIndoorPlay",
    "outdoorPlay": "lastOutdoorPlay",
    "screenTime": "lastScreenTime",
    "skinToSkin": "lastSkinToSkin",
    "storyTime": "lastStoryTime",
    "tummyTime": "lastTummyTime",
}
ACTIVITY_TRANSLATION_KEYS: Final[dict[ActivityMode, str]] = {
    "bath": "activity_bath",
    "brushTeeth": "activity_brush_teeth",
    "indoorPlay": "activity_indoor_play",
    "outdoorPlay": "activity_outdoor_play",
    "screenTime": "activity_screen_time",
    "skinToSkin": "activity_skin_to_skin",
    "storyTime": "activity_story_time",
    "tummyTime": "activity_tummy_time",
}
ACTIVITY_LABELS: Final[dict[ActivityMode, str]] = {
    "bath": "Bath",
    "brushTeeth": "Brush Teeth",
    "indoorPlay": "Indoor Play",
    "outdoorPlay": "Outdoor Play",
    "screenTime": "Screen Time",
    "skinToSkin": "Skin to Skin",
    "storyTime": "Story Time",
    "tummyTime": "Tummy Time",
}
ACTIVITY_STATE_OPTIONS: Final[list[str]] = ["active", "paused", "none"]


def _last_activity(
    status: FirebaseActivityDocumentData | None,
    mode: ActivityMode,
) -> FirebaseLastActivityData | None:
    """Return the last completed session for an activity mode."""
    prefs = status.prefs if status is not None else None
    if prefs is None:
        return None

    last_activity = getattr(prefs, ACTIVITY_LAST_FIELDS[mode], None)
    return last_activity if isinstance(last_activity, FirebaseLastActivityData) else None


def _timer_entry(
    status: FirebaseActivityDocumentData | None,
    mode: ActivityMode,
) -> FirebaseActivityTimerEntryData | None:
    """Return the timer entry for an activity mode."""
    timer = status.timer if status is not None else None
    if timer is None:
        return None

    entry = getattr(timer, mode, None)
    return entry if isinstance(entry, FirebaseActivityTimerEntryData) else None


def _active_activity_mode(
    status: FirebaseActivityDocumentData | None,
) -> ActivityMode | None:
    """Return the activity mode whose timer is running or paused."""
    for mode in ACTIVITY_MODES:
        entry = _timer_entry(status, mode)
        if entry is not None and entry.active:
            return mode
    return None


def _activity_completion_time(last_activity: FirebaseLastActivityData) -> float | None:
    """Return when a completed session ended, falling back to its start."""
    if last_activity.start is None:
        return None
    start = float(last_activity.start)
    if last_activity.duration is None:
        return start
    return start + float(last_activity.duration)


def _latest_completed_activity(
    status: FirebaseActivityDocumentData | None,
) -> tuple[ActivityMode, FirebaseLastActivityData] | None:
    """Return the most recently completed activity across all modes."""
    latest: tuple[ActivityMode, FirebaseLastActivityData] | None = None
    latest_completion: float | None = None
    for mode in ACTIVITY_MODES:
        last_activity = _last_activity(status, mode)
        completion = (
            _activity_completion_time(last_activity)
            if last_activity is not None
            else None
        )
        if last_activity is None or completion is None:
            continue

        if latest_completion is None or completion > latest_completion:
            latest = (mode, last_activity)
            latest_completion = completion
    return latest


def activity_mode_has_entry(
    status: FirebaseActivityDocumentData | None,
    mode: ActivityMode,
) -> bool:
    """Return whether a mode has a completed session."""
    last_activity = _last_activity(status, mode)
    return last_activity is not None and last_activity.start is not None


def build_activity_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build activity sensors."""
    entities: list[SensorEntity] = []
    for child in children:
        entities.extend(
            HuckleberryActivitySensor(coordinator, child, mode)
            for mode in ACTIVITY_MODES
        )
        entities.append(HuckleberryActivityTimerSensor(coordinator, child))
    return entities


class HuckleberryActivitySensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the last completed session for one activity mode."""

    _attr_icon = "mdi:teddy-bear"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
        mode: ActivityMode,
    ) -> None:
        super().__init__(coordinator, child)
        self._mode = mode
        self._attr_translation_key = ACTIVITY_TRANSLATION_KEYS[mode]
        self._attr_unique_id = f"{self.child_uid}_{self._attr_translation_key}"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return True when this mode already has a completed session."""
        return self.has_activity_entry

    @property
    def mode(self) -> ActivityMode:
        """Return the activity mode."""
        return self._mode

    @property
    def has_activity_entry(self) -> bool:
        """Return whether this mode has a completed session."""
        return activity_mode_has_entry(
            self.coordinator.get_activity_status(self.child_uid), self._mode
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the last completed activity timestamp."""
        last_activity = _last_activity(
            self.coordinator.get_activity_status(self.child_uid), self._mode
        )
        return as_datetime(last_activity.start if last_activity is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return the last completed activity details."""
        last_activity = _last_activity(
            self.coordinator.get_activity_status(self.child_uid), self._mode
        )
        if last_activity is None:
            return {}

        attributes: dict[str, object] = {}
        if last_activity.start is not None:
            attributes["time"] = as_iso8601_datetime(last_activity.start)
        if last_activity.duration is not None:
            attributes["duration"] = as_iso8601_duration(last_activity.duration)
        return attributes


class HuckleberryActivityTimerSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the shared activity timer status."""

    _attr_icon = "mdi:timer"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ACTIVITY_STATE_OPTIONS
    _attr_entity_registry_enabled_default = True
    _attr_translation_key = "activity"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_activity"

    @property
    def native_value(self) -> str | None:
        """Return the activity timer state."""
        status = self.coordinator.get_activity_status(self.child_uid)
        if status is None or status.timer is None:
            return None

        mode = _active_activity_mode(status)
        if mode is None:
            return "none"

        entry = _timer_entry(status, mode)
        return "paused" if entry is not None and entry.paused else "active"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return the current and previous activity details."""
        status = self.coordinator.get_activity_status(self.child_uid)
        if status is None:
            return {}

        attributes: dict[str, object] = {}

        mode = _active_activity_mode(status)
        entry = _timer_entry(status, mode) if mode is not None else None
        if mode is not None and entry is not None:
            attributes["current_mode"] = ACTIVITY_LABELS[mode]
            if entry.startTime is not None:
                attributes["current_start"] = as_iso8601_datetime(entry.startTime)
            if entry.paused and entry.endTime is not None:
                attributes["current_end"] = as_iso8601_datetime(entry.endTime)

        latest = _latest_completed_activity(status)
        if latest is not None:
            previous_mode, previous = latest
            attributes["previous_mode"] = ACTIVITY_LABELS[previous_mode]
            if previous.start is not None:
                attributes["previous_start"] = as_iso8601_datetime(previous.start)
            if previous.duration is not None:
                attributes["previous_duration"] = as_iso8601_duration(
                    previous.duration
                )

        return attributes


def setup_activity_sensor_activation(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
    sensors: list[SensorEntity],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Enable and add activity sensors as their modes gain completed sessions."""
    last_activity_sensors = [
        sensor for sensor in sensors if isinstance(sensor, HuckleberryActivitySensor)
    ]
    if not last_activity_sensors:
        return

    children_by_uid = {child.uid: child for child in children}
    handled_modes: set[tuple[str, ActivityMode]] = set()
    registry = er.async_get(hass)

    @callback
    def _async_sync_activity_sensors() -> None:
        """Enable and add activity sensors whose mode has a completed session."""
        if entry.pref_disable_new_entities:
            return

        new_entities: list[SensorEntity] = []
        for sensor in last_activity_sensors:
            unique_id = sensor.unique_id
            mode_key = (sensor.child_uid, sensor.mode)
            if (
                unique_id is None
                or mode_key in handled_modes
                or not sensor.has_activity_entry
            ):
                continue

            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id is None:
                continue

            registry_entry = registry.async_get(entity_id)
            if registry_entry is None:
                continue
            if registry_entry.disabled_by is RegistryEntryDisabler.INTEGRATION:
                registry.async_update_entity(entity_id, disabled_by=None)
            elif registry_entry.disabled_by is not None:
                handled_modes.add(mode_key)
                continue
            elif hass.states.get(entity_id) is not None:
                handled_modes.add(mode_key)
                continue
            else:
                # The platform is already adding an enabled entity.
                continue

            handled_modes.add(mode_key)
            child = children_by_uid.get(sensor.child_uid)
            if child is not None:
                new_entities.append(
                    HuckleberryActivitySensor(coordinator, child, sensor.mode)
                )

        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_sync_activity_sensors))
    _async_sync_activity_sensors()

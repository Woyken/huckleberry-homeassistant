"""Activity-related entities for Huckleberry."""
from __future__ import annotations

from datetime import datetime
from typing import Final, cast, get_args

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from huckleberry_api.firebase_types import (
    ActivityMode,
    FirebaseActivityDocumentData,
    FirebaseActivityTimerEntryData,
    FirebaseLastActivityData,
)

from .. import HuckleberryDataUpdateCoordinator
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


def _latest_completed_activity(
    status: FirebaseActivityDocumentData | None,
) -> tuple[ActivityMode, FirebaseLastActivityData] | None:
    """Return the most recently completed activity across all modes."""
    latest: tuple[ActivityMode, FirebaseLastActivityData] | None = None
    latest_start: float | None = None
    for mode in ACTIVITY_MODES:
        last_activity = _last_activity(status, mode)
        if last_activity is None or last_activity.start is None:
            continue

        start = float(last_activity.start)
        if latest_start is None or start > latest_start:
            latest = (mode, last_activity)
            latest_start = start
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
        self._attr_entity_registry_enabled_default = activity_mode_has_entry(
            coordinator.get_activity_status(self.child_uid), mode
        )

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

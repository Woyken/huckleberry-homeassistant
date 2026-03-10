"""Calendar platform for Huckleberry integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from huckleberry_api import HuckleberryAPI
from huckleberry_api.firebase_types import (
    FirebaseBottleFeedIntervalData,
    FirebaseBreastFeedIntervalData,
    FirebaseDiaperData,
    FirebaseGrowthData,
    FirebaseSleepIntervalData,
    FirebaseSolidsFeedIntervalData,
)

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
    """Set up Huckleberry calendar from a config entry."""
    data: HuckleberryEntryData = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinator = data["coordinator"]
    children = data["children"]

    entities = []
    for child in children:
        entities.append(HuckleberryCalendar(coordinator, child, api))

    async_add_entities(entities)


class HuckleberryCalendar(HuckleberryBaseEntity, CalendarEntity):
    """Calendar entity for Huckleberry events."""

    _attr_has_entity_name = True
    _attr_name = "Events"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
        api: HuckleberryAPI,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, child)
        self._api = api
        self._attr_unique_id = f"{child.uid}_calendar"
        self._events: list[CalendarEvent] = []

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        upcoming = [e for e in self._events if e.start > now]
        return min(upcoming, key=lambda e: e.start) if upcoming else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Get events between start and end date."""
        _LOGGER.debug(
            "Fetching calendar events for %s from %s to %s",
            self.child_name,
            start_date,
            end_date,
        )

        start_s = int(start_date.timestamp())
        end_s = int(end_date.timestamp())

        events: list[CalendarEvent] = []

        try:
            sleep_intervals = await self._api.list_sleep_intervals(
                self.child_uid, start_s, end_s
            )
            events.extend(self._build_sleep_events(sleep_intervals))
        except Exception as err:
            _LOGGER.error("Error fetching sleep events: %s", err)

        try:
            feed_intervals = await self._api.list_feed_intervals(
                self.child_uid, start_s, end_s
            )
            feed_events, bottle_events = self._build_feed_events(feed_intervals)
            events.extend(feed_events)
            events.extend(bottle_events)
        except Exception as err:
            _LOGGER.error("Error fetching feed events: %s", err)

        try:
            diaper_intervals = await self._api.list_diaper_intervals(
                self.child_uid, start_s, end_s
            )
            events.extend(self._build_diaper_events(diaper_intervals))
        except Exception as err:
            _LOGGER.error("Error fetching diaper events: %s", err)

        try:
            health_entries = await self._api.list_health_entries(
                self.child_uid, start_s, end_s
            )
            events.extend(self._build_health_events(health_entries))
        except Exception as err:
            _LOGGER.error("Error fetching health events: %s", err)

        events.sort(key=lambda e: e.start)
        self._events = events
        _LOGGER.debug("Found %d events for %s", len(events), self.child_name)
        return events

    @staticmethod
    def _build_sleep_events(
        intervals: list[FirebaseSleepIntervalData],
    ) -> list[CalendarEvent]:
        """Build calendar events from sleep intervals."""
        events: list[CalendarEvent] = []
        for interval in intervals:
            start_time = datetime.fromtimestamp(
                interval.start, tz=dt_util.DEFAULT_TIME_ZONE
            )
            duration_seconds = int(interval.duration)
            duration_minutes = duration_seconds // 60
            end_time = start_time + timedelta(minutes=duration_minutes)

            if duration_minutes >= 60:
                hours = duration_minutes // 60
                mins = duration_minutes % 60
                duration_str = f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
            else:
                duration_str = f"{duration_minutes}m"

            events.append(
                CalendarEvent(
                    start=start_time,
                    end=end_time,
                    summary=f"💤 Sleep ({duration_str})",
                    description=f"Sleep duration: {duration_str}",
                )
            )
        return events

    @staticmethod
    def _build_feed_events(
        intervals: list[
            FirebaseBreastFeedIntervalData
            | FirebaseBottleFeedIntervalData
            | FirebaseSolidsFeedIntervalData
        ],
    ) -> tuple[list[CalendarEvent], list[CalendarEvent]]:
        """Build calendar events from feed intervals."""
        feed_events: list[CalendarEvent] = []
        bottle_events: list[CalendarEvent] = []

        for interval in intervals:
            start_time = datetime.fromtimestamp(
                interval.start, tz=dt_util.DEFAULT_TIME_ZONE
            )

            if isinstance(interval, FirebaseBottleFeedIntervalData):
                amount = interval.amount
                units = interval.units
                bottle_type = interval.bottleType

                summary = f"🍼 Bottle ({amount} {units})"
                description = f"Bottle feeding: {amount} {units}"
                if bottle_type:
                    description += f"\nType: {bottle_type}"

                bottle_events.append(
                    CalendarEvent(
                        start=start_time,
                        end=start_time,
                        summary=summary,
                        description=description,
                    )
                )
                continue

            if isinstance(interval, FirebaseBreastFeedIntervalData):
                left_duration_seconds = float(interval.leftDuration or 0)
                right_duration_seconds = float(interval.rightDuration or 0)

                total_duration_seconds = int(
                    round(left_duration_seconds + right_duration_seconds)
                )
                end_time = start_time + timedelta(seconds=total_duration_seconds)

                left_minutes = int(round(left_duration_seconds / 60))
                right_minutes = int(round(right_duration_seconds / 60))

                sides: list[str] = []
                if left_minutes > 0:
                    sides.append(f"L:{left_minutes}m")
                if right_minutes > 0:
                    sides.append(f"R:{right_minutes}m")

                sides_str = (
                    " ".join(sides)
                    if sides
                    else _format_duration(total_duration_seconds)
                )
                summary = f"🍼 Feed ({sides_str})"
                description = f"Feeding - Total: {_format_duration(total_duration_seconds)}"
                if left_duration_seconds > 0:
                    description += f"\nLeft: {_format_duration(left_duration_seconds)}"
                if right_duration_seconds > 0:
                    description += f"\nRight: {_format_duration(right_duration_seconds)}"

                feed_events.append(
                    CalendarEvent(
                        start=start_time,
                        end=end_time,
                        summary=summary,
                        description=description,
                    )
                )
                continue

            # Solids
            summary = "🥄 Solids"
            description = "Solid food feeding"
            if interval.notes:
                description += f"\n{interval.notes}"

            feed_events.append(
                CalendarEvent(
                    start=start_time,
                    end=start_time,
                    summary=summary,
                    description=description,
                )
            )

        return feed_events, bottle_events

    @staticmethod
    def _build_diaper_events(
        intervals: list[FirebaseDiaperData],
    ) -> list[CalendarEvent]:
        """Build calendar events from diaper intervals."""
        events: list[CalendarEvent] = []
        for interval in intervals:
            event_time = datetime.fromtimestamp(
                interval.start, tz=dt_util.DEFAULT_TIME_ZONE
            )
            mode = interval.mode
            mode_emoji = {
                "pee": "💧",
                "poo": "💩",
                "both": "💧💩",
                "dry": "✅",
            }.get(mode, "🩲")

            summary = f"{mode_emoji} Diaper ({mode.capitalize()})"
            description = f"Diaper change: {mode}"

            if interval.color is not None:
                description += f"\nColor: {interval.color}"
            if interval.consistency is not None:
                description += f"\nConsistency: {interval.consistency}"

            events.append(
                CalendarEvent(
                    start=event_time,
                    end=event_time,
                    summary=summary,
                    description=description,
                )
            )
        return events

    @staticmethod
    def _build_health_events(entries: list) -> list[CalendarEvent]:
        """Build calendar events from health entries."""
        events: list[CalendarEvent] = []
        for entry in entries:
            event_time = datetime.fromtimestamp(
                entry.start, tz=dt_util.DEFAULT_TIME_ZONE
            )

            if isinstance(entry, FirebaseGrowthData):
                summary = "📏 Growth Measurement"
                description = "Growth tracking:"
                measurements: list[str] = []
                if entry.weight is not None:
                    measurements.append(f"Weight: {entry.weight}")
                if entry.height is not None:
                    measurements.append(f"Height: {entry.height}")
                if entry.head is not None:
                    measurements.append(f"Head: {entry.head}")
                if measurements:
                    description += "\n" + "\n".join(measurements)
            else:
                summary = f"🩺 Health ({entry.mode.capitalize()})"
                description = f"Health entry: {entry.mode}"

            events.append(
                CalendarEvent(
                    start=event_time,
                    end=event_time,
                    summary=summary,
                    description=description,
                )
            )
        return events


def _format_duration(duration_seconds: float | int) -> str:
    """Format duration in seconds as readable min/sec text."""
    total_seconds = int(round(float(duration_seconds)))
    minutes, seconds = divmod(total_seconds, 60)

    if minutes > 0 and seconds > 0:
        return f"{minutes} min {seconds} sec"
    if minutes > 0:
        return f"{minutes} min"
    return f"{seconds} sec"

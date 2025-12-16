"""Calendar platform for Huckleberry integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import HuckleberryEntryData
from .const import DOMAIN
from .entity import HuckleberryBaseEntity

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

    def __init__(self, coordinator, child, api) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, child)
        self._api = api
        self._attr_unique_id = f"{child['uid']}_calendar"
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
            self._child["name"],
            start_date,
            end_date,
        )

        events: list[CalendarEvent] = []

        # Fetch sleep intervals
        events.extend(
            await self.hass.async_add_executor_job(
                self._fetch_sleep_events, start_date, end_date
            )
        )

        # Fetch feeding intervals
        events.extend(
            await self.hass.async_add_executor_job(
                self._fetch_feed_events, start_date, end_date
            )
        )

        # Fetch diaper intervals
        events.extend(
            await self.hass.async_add_executor_job(
                self._fetch_diaper_events, start_date, end_date
            )
        )

        # Fetch health/growth entries
        events.extend(
            await self.hass.async_add_executor_job(
                self._fetch_health_events, start_date, end_date
            )
        )

        # Sort by start time
        events.sort(key=lambda e: e.start)

        self._events = events
        _LOGGER.debug("Found %d events for %s", len(events), self._child["name"])

        return events

    def _fetch_sleep_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Fetch sleep intervals using API."""
        events = []
        child_uid = self._child["uid"]

        try:
            # Convert to timestamps (seconds)
            start_s = int(start_date.timestamp())
            end_s = int(end_date.timestamp())

            # Fetch intervals from API
            intervals = self._api.get_sleep_intervals(child_uid, start_s, end_s)

            for interval in intervals:
                start_time = datetime.fromtimestamp(
                    interval["start"], tz=dt_util.DEFAULT_TIME_ZONE
                )

                duration_seconds = interval.get("duration", 0)
                duration_minutes = int(duration_seconds / 60)
                end_time = start_time + timedelta(minutes=duration_minutes)

                # Format duration as hours and minutes
                if duration_minutes >= 60:
                    hours = duration_minutes // 60
                    mins = duration_minutes % 60
                    duration_str = f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
                else:
                    duration_str = f"{duration_minutes}m"

                summary = f"💤 Sleep ({duration_str})"
                description = f"Sleep duration: {duration_str}"

                events.append(
                    CalendarEvent(
                        start=start_time,
                        end=end_time,
                        summary=summary,
                        description=description,
                    )
                )

            _LOGGER.debug("Found %d sleep events", len(events))

        except Exception as err:
            _LOGGER.error("Error fetching sleep events: %s", err)

        return events

    def _fetch_feed_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Fetch feeding intervals using API."""
        events = []
        child_uid = self._child["uid"]

        try:
            # Convert to timestamps (seconds)
            start_s = int(start_date.timestamp())
            end_s = int(end_date.timestamp())

            # Fetch intervals from API
            intervals = self._api.get_feed_intervals(child_uid, start_s, end_s)

            for interval in intervals:
                start_time = datetime.fromtimestamp(
                    interval["start"], tz=dt_util.DEFAULT_TIME_ZONE
                )

                # Check if this is a multi-entry document (durations in seconds)
                # or regular document (durations in minutes)
                if interval.get("is_multi_entry"):
                    # Multi-entry: durations are in SECONDS, convert to minutes
                    left_duration = round(interval.get("leftDuration", 0) / 60)
                    right_duration = round(interval.get("rightDuration", 0) / 60)
                else:
                    # Regular doc: durations are in minutes
                    left_duration = int(interval.get("leftDuration", 0))
                    right_duration = int(interval.get("rightDuration", 0))

                total_duration = left_duration + right_duration
                end_time = start_time + timedelta(minutes=total_duration)

                # Build summary based on sides used
                sides = []
                if left_duration > 0:
                    sides.append(f"L:{left_duration}m")
                if right_duration > 0:
                    sides.append(f"R:{right_duration}m")

                sides_str = " ".join(sides) if sides else f"{total_duration}m"
                summary = f"🍼 Feed ({sides_str})"
                description = f"Feeding - Total: {total_duration} minutes"
                if left_duration > 0:
                    description += f"\nLeft: {left_duration} minutes"
                if right_duration > 0:
                    description += f"\nRight: {right_duration} minutes"

                events.append(
                    CalendarEvent(
                        start=start_time,
                        end=end_time,
                        summary=summary,
                        description=description,
                    )
                )

            _LOGGER.debug("Found %d feed events", len(events))

        except Exception as err:
            _LOGGER.error("Error fetching feed events: %s", err)

        return events

    def _fetch_diaper_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Fetch diaper intervals using API."""
        events = []
        child_uid = self._child["uid"]

        try:
            # Convert to timestamps (seconds)
            start_s = int(start_date.timestamp())
            end_s = int(end_date.timestamp())

            # Fetch intervals from API
            intervals = self._api.get_diaper_intervals(child_uid, start_s, end_s)

            for interval in intervals:
                event_time = datetime.fromtimestamp(
                    interval["start"], tz=dt_util.DEFAULT_TIME_ZONE
                )

                # Diaper change is an instant event (same start/end)
                mode = interval.get("mode", "unknown")
                mode_emoji = {
                    "pee": "💧",
                    "poo": "💩",
                    "both": "💧💩",
                    "dry": "✅",
                }.get(mode, "🩲")

                summary = f"{mode_emoji} Diaper ({mode.capitalize()})"
                description = f"Diaper change: {mode}"

                # Add details if available
                if "pooColor" in interval:
                    description += f"\nColor: {interval['pooColor']}"
                if "pooConsistency" in interval:
                    description += f"\nConsistency: {interval['pooConsistency']}"
                if "amount" in interval:
                    description += f"\nAmount: {interval['amount']}"

                events.append(
                    CalendarEvent(
                        start=event_time,
                        end=event_time,
                        summary=summary,
                        description=description,
                    )
                )

            _LOGGER.debug("Found %d diaper events", len(events))

        except Exception as err:
            _LOGGER.error("Error fetching diaper events: %s", err)

        return events

    def _fetch_health_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Fetch health/growth entries using API."""
        events = []
        child_uid = self._child["uid"]

        try:
            # Convert to timestamps (seconds)
            start_s = int(start_date.timestamp())
            end_s = int(end_date.timestamp())

            # Fetch entries from API
            entries = self._api.get_health_entries(child_uid, start_s, end_s)

            for entry in entries:
                event_time = datetime.fromtimestamp(
                    entry["start"], tz=dt_util.DEFAULT_TIME_ZONE
                )

                # Growth entry is an instant event
                summary = "📏 Growth Measurement"
                description = "Growth tracking:"

                # Build description from available measurements
                measurements = []
                if "weight" in entry:
                    measurements.append(f"Weight: {entry['weight']}")
                if "height" in entry:
                    measurements.append(f"Height: {entry['height']}")
                if "head" in entry:
                    measurements.append(f"Head: {entry['head']}")

                if measurements:
                    description += "\n" + "\n".join(measurements)

                events.append(
                    CalendarEvent(
                        start=event_time,
                        end=event_time,
                        summary=summary,
                        description=description,
                    )
                )

            _LOGGER.debug("Found %d health events", len(events))

        except Exception as err:
            _LOGGER.error("Error fetching health events: %s", err)

        return events

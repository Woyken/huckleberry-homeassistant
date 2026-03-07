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
        events.extend(await self._fetch_sleep_events(start_date, end_date))

        # Fetch feeding intervals
        feed_events, bottle_events = await self._fetch_feed_and_bottle_events(start_date, end_date)
        events.extend(feed_events)
        events.extend(bottle_events)

        # Fetch diaper intervals
        events.extend(await self._fetch_diaper_events(start_date, end_date))

        # Fetch health/growth entries
        events.extend(await self._fetch_health_events(start_date, end_date))

        # Sort by start time
        events.sort(key=lambda e: e.start)

        self._events = events
        _LOGGER.debug("Found %d events for %s", len(events), self._child["name"])

        return events

    @staticmethod
    def _as_interval_dict(item: Any) -> dict[str, Any]:
        """Normalize API interval models into mapping objects."""
        if isinstance(item, dict):
            return item

        model_dump = getattr(item, "model_dump", None)
        if callable(model_dump):
            data = model_dump(by_alias=True, exclude_none=True)
            if isinstance(data, dict):
                return data

        return {}

    async def _fetch_sleep_events(
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
            intervals = await self._api.list_sleep_intervals(child_uid, start_s, end_s)

            for interval in intervals:
                interval_data = self._as_interval_dict(interval)
                start_time = datetime.fromtimestamp(
                    interval_data["start"], tz=dt_util.DEFAULT_TIME_ZONE
                )

                duration_seconds = interval_data.get("duration", 0)
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

    async def _fetch_feed_and_bottle_events(
        self, start_date: datetime, end_date: datetime
    ) -> tuple[list[CalendarEvent], list[CalendarEvent]]:
        """Fetch feed and bottle intervals using a single API call."""
        feed_events: list[CalendarEvent] = []
        bottle_events: list[CalendarEvent] = []
        child_uid = self._child["uid"]

        try:
            # Convert to timestamps (seconds)
            start_s = int(start_date.timestamp())
            end_s = int(end_date.timestamp())

            intervals = await self._api.list_feed_intervals(child_uid, start_s, end_s)

            for interval in intervals:
                interval_data = self._as_interval_dict(interval)
                start_time = datetime.fromtimestamp(
                    interval_data["start"], tz=dt_util.DEFAULT_TIME_ZONE
                )

                if self._is_bottle_interval(interval_data):
                    # Bottle feeding is an instant event (same start/end)
                    amount = interval_data.get("amount", interval_data.get("bottleAmount", 0))
                    units = interval_data.get("units", interval_data.get("bottleUnits", "ml"))
                    bottle_type = interval_data.get("bottleType", "Unknown")

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

                # Feed interval durations are stored in seconds.
                left_duration_seconds = float(interval_data.get("leftDuration", 0) or 0)
                right_duration_seconds = float(interval_data.get("rightDuration", 0) or 0)

                total_duration_seconds = int(
                    round(left_duration_seconds + right_duration_seconds)
                )
                end_time = start_time + timedelta(seconds=total_duration_seconds)

                left_duration = int(round(left_duration_seconds / 60))
                right_duration = int(round(right_duration_seconds / 60))

                # Build summary based on sides used
                sides = []
                if left_duration > 0:
                    sides.append(f"L:{left_duration}m")
                if right_duration > 0:
                    sides.append(f"R:{right_duration}m")

                sides_str = (
                    " ".join(sides)
                    if sides
                    else self._format_duration(total_duration_seconds)
                )
                summary = f"🍼 Feed ({sides_str})"
                description = (
                    f"Feeding - Total: {self._format_duration(total_duration_seconds)}"
                )
                if left_duration_seconds > 0:
                    description += f"\nLeft: {self._format_duration(left_duration_seconds)}"
                if right_duration_seconds > 0:
                    description += f"\nRight: {self._format_duration(right_duration_seconds)}"

                feed_events.append(
                    CalendarEvent(
                        start=start_time,
                        end=end_time,
                        summary=summary,
                        description=description,
                    )
                )

            _LOGGER.debug("Found %d feed events", len(feed_events))
            _LOGGER.debug("Found %d bottle events", len(bottle_events))

        except Exception as err:
            _LOGGER.error("Error fetching feed and bottle events: %s", err)

        return feed_events, bottle_events

    @staticmethod
    def _is_bottle_interval(interval: dict[str, Any]) -> bool:
        """Return True if interval represents a bottle feeding event."""
        return (
            interval.get("mode") == "bottle"
            or interval.get("type") == "bottle"
            or interval.get("bottleType") is not None
            or "amount" in interval
            or "bottleAmount" in interval
        )

    @staticmethod
    def _format_duration(duration_seconds: float | int) -> str:
        """Format duration in seconds as readable min/sec text."""
        total_seconds = int(round(float(duration_seconds)))
        minutes, seconds = divmod(total_seconds, 60)

        if minutes > 0 and seconds > 0:
            return f"{minutes} min {seconds} sec"
        if minutes > 0:
            return f"{minutes} min"
        return f"{seconds} sec"

    async def _fetch_diaper_events(
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
            intervals = await self._api.list_diaper_intervals(child_uid, start_s, end_s)

            for interval in intervals:
                interval_data = self._as_interval_dict(interval)
                event_time = datetime.fromtimestamp(
                    interval_data["start"], tz=dt_util.DEFAULT_TIME_ZONE
                )

                # Diaper change is an instant event (same start/end)
                mode = interval_data.get("mode", "unknown")
                mode_emoji = {
                    "pee": "💧",
                    "poo": "💩",
                    "both": "💧💩",
                    "dry": "✅",
                }.get(mode, "🩲")

                summary = f"{mode_emoji} Diaper ({mode.capitalize()})"
                description = f"Diaper change: {mode}"

                # Add details if available
                if "color" in interval_data:
                    description += f"\nColor: {interval_data['color']}"
                if "consistency" in interval_data:
                    description += f"\nConsistency: {interval_data['consistency']}"
                quantity = interval_data.get("quantity", {})
                if isinstance(quantity, dict):
                    if quantity.get("pee") is not None:
                        description += f"\nPee amount: {quantity['pee']}"
                    if quantity.get("poo") is not None:
                        description += f"\nPoo amount: {quantity['poo']}"

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

    async def _fetch_health_events(
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
            entries = await self._api.list_health_entries(child_uid, start_s, end_s)

            for entry in entries:
                entry_data = self._as_interval_dict(entry)
                event_time = datetime.fromtimestamp(
                    entry_data["start"], tz=dt_util.DEFAULT_TIME_ZONE
                )

                # Growth entry is an instant event
                summary = "📏 Growth Measurement"
                description = "Growth tracking:"

                # Build description from available measurements
                measurements = []
                if "weight" in entry_data:
                    measurements.append(f"Weight: {entry_data['weight']}")
                if "height" in entry_data:
                    measurements.append(f"Height: {entry_data['height']}")
                if "head" in entry_data:
                    measurements.append(f"Head: {entry_data['head']}")

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

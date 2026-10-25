"""Calendar platform for Huckleberry integration."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from huckleberry_api import HuckleberryAPI

from . import HuckleberryDataUpdateCoordinator, HuckleberryEntryData
from .const import DOMAIN
from .entity import HuckleberryBaseEntity
from .features.calendar_events import (
    build_activity_events,
    build_diaper_events,
    build_feed_events,
    build_health_events,
    build_pump_events,
    build_sleep_events,
)
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
    _attr_translation_key = "events"

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

        events: list[CalendarEvent] = []

        try:
            sleep_intervals = await self._api.list_sleep_intervals(
                self.child_uid, start_date, end_date
            )
            events.extend(build_sleep_events(sleep_intervals))
        except Exception as err:
            _LOGGER.error("Error fetching sleep events: %s", err)

        try:
            feed_intervals = await self._api.list_feed_intervals(
                self.child_uid, start_date, end_date
            )
            feed_events, bottle_events = build_feed_events(feed_intervals)
            events.extend(feed_events)
            events.extend(bottle_events)
        except Exception as err:
            _LOGGER.error("Error fetching feed events: %s", err)

        try:
            diaper_intervals = await self._api.list_diaper_intervals(
                self.child_uid, start_date, end_date
            )
            events.extend(build_diaper_events(diaper_intervals))
        except Exception as err:
            _LOGGER.error("Error fetching diaper events: %s", err)

        try:
            health_entries = await self._api.list_health_entries(
                self.child_uid, start_date, end_date
            )
            events.extend(build_health_events(health_entries))
        except Exception as err:
            _LOGGER.error("Error fetching health events: %s", err)

        try:
            pump_intervals = await self._api.list_pump_intervals(
                self.child_uid, start_date, end_date
            )
            events.extend(build_pump_events(pump_intervals))
        except Exception as err:
            _LOGGER.error("Error fetching pump events: %s", err)

        try:
            activity_intervals = await self._api.list_activity_intervals(
                self.child_uid, start_date, end_date
            )
            events.extend(build_activity_events(activity_intervals))
        except Exception as err:
            _LOGGER.error("Error fetching activity events: %s", err)

        events.sort(key=lambda e: e.start)
        self._events = events
        _LOGGER.debug("Found %d events for %s", len(events), self.child_name)
        return events

"""Test calendar platform."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.components.calendar import CalendarEvent
from homeassistant.util import dt as dt_util

from custom_components.huckleberry.calendar import HuckleberryCalendar


@pytest.fixture
def mock_api():
    """Create a mock API."""
    api = MagicMock()
    api._get_firestore_client = MagicMock()
    return api


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {}
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    return entry


@pytest.fixture
def child_data():
    """Create mock child data."""
    return {
        "uid": "test_child_uid",
        "name": "Test Baby",
        "birthdate": "2024-01-01",
    }


@pytest.fixture
def calendar(mock_api, mock_coordinator, child_data, mock_entry):
    """Create a calendar instance."""
    return HuckleberryCalendar(mock_coordinator, child_data, mock_api)


def test_calendar_attributes(calendar, child_data):
    """Test calendar entity attributes."""
    assert calendar.unique_id == "test_child_uid_calendar"
    assert calendar.name == "Events"
    assert calendar._child == child_data


@pytest.mark.asyncio
async def test_async_get_events(calendar, hass):
    """Test async get events integration."""
    calendar.hass = hass

    # Mock all fetch methods
    with patch.object(
        calendar, "_fetch_sleep_events", return_value=[]
    ), patch.object(
        calendar, "_fetch_feed_and_bottle_events", return_value=([], [])
    ), patch.object(
        calendar, "_fetch_diaper_events", return_value=[]
    ), patch.object(
        calendar, "_fetch_health_events", return_value=[]
    ):
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)

        events = await calendar.async_get_events(hass, start_date, end_date)

        assert isinstance(events, list)
        assert len(events) == 0  # All mocked to return empty lists


def test_fetch_feed_and_bottle_events_splits_intervals(calendar):
    """Feed and bottle intervals should be split from one API response."""
    calendar._api.get_feed_intervals.return_value = [
        {
            "start": 1700000000,
            "leftDuration": 900,
            "rightDuration": 600,
            "is_multi_entry": False,
            "mode": "breast",
        },
        {
            "start": 1700000600,
            "leftDuration": 0,
            "rightDuration": 0,
            "is_multi_entry": False,
            "mode": "bottle",
            "amount": 120,
            "units": "ml",
        },
    ]

    feed_events, bottle_events = calendar._fetch_feed_and_bottle_events(
        datetime.now(), datetime.now() + timedelta(days=1)
    )

    assert len(feed_events) == 1
    assert len(bottle_events) == 1
    assert feed_events[0].summary.startswith("🍼 Feed")
    assert "L:15m" in feed_events[0].summary
    assert "R:10m" in feed_events[0].summary
    assert bottle_events[0].summary == "🍼 Bottle (120 ml)"


def test_fetch_feed_and_bottle_events_formats_feed_description(calendar):
    """Feed event descriptions should format seconds as min/sec text."""
    calendar._api.get_feed_intervals.return_value = [
        {
            "start": 1700000000,
            "leftDuration": 111,
            "rightDuration": 103,
            "is_multi_entry": False,
            "mode": "breast",
        },
    ]

    feed_events, bottle_events = calendar._fetch_feed_and_bottle_events(
        datetime.now(), datetime.now() + timedelta(days=1)
    )

    assert len(feed_events) == 1
    assert len(bottle_events) == 0
    assert "Feeding - Total: 3 min 34 sec" in (feed_events[0].description or "")
    assert "Left: 1 min 51 sec" in (feed_events[0].description or "")
    assert "Right: 1 min 43 sec" in (feed_events[0].description or "")


def test_fetch_feed_and_bottle_events_extracts_bottle_event(calendar):
    """Bottle intervals should render as bottle events."""
    calendar._api.get_feed_intervals.return_value = [
        {
            "start": 1700000600,
            "leftDuration": 0,
            "rightDuration": 0,
            "is_multi_entry": False,
            "mode": "bottle",
            "bottleType": "Formula",
            "amount": 120,
            "units": "ml",
        },
        {
            "start": 1700001200,
            "leftDuration": 20,
            "rightDuration": 0,
            "is_multi_entry": False,
            "mode": "breast",
        },
    ]

    feed_events, bottle_events = calendar._fetch_feed_and_bottle_events(
        datetime.now(), datetime.now() + timedelta(days=1)
    )

    assert len(feed_events) == 1
    assert len(bottle_events) == 1
    assert bottle_events[0].summary == "🍼 Bottle (120 ml)"
    assert "Type: Formula" in (bottle_events[0].description or "")

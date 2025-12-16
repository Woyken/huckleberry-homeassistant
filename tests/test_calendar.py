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
        calendar, "_fetch_feed_events", return_value=[]
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

"""Test calendar platform."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

from huckleberry_api.firebase_types import (
    FirebaseBottleFeedIntervalData,
    FirebaseBreastFeedIntervalData,
    FirebaseChildDocument,
    FirebaseUserChildRef,
)

from custom_components.huckleberry.calendar import HuckleberryCalendar
from custom_components.huckleberry.models import HuckleberryChildProfile


def _make_profile(uid: str = "test_child_uid", name: str = "Test Baby") -> HuckleberryChildProfile:
    return HuckleberryChildProfile(
        uid=uid,
        reference=FirebaseUserChildRef(cid=uid),
        document=FirebaseChildDocument(childsName=name, birthdate="2024-01-01"),
    )


@pytest.fixture
def mock_api():
    """Create a mock API."""
    api = MagicMock()
    api.list_sleep_intervals = AsyncMock(return_value=[])
    api.list_feed_intervals = AsyncMock(return_value=[])
    api.list_diaper_intervals = AsyncMock(return_value=[])
    api.list_health_entries = AsyncMock(return_value=[])
    return api


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {}
    return coordinator


@pytest.fixture
def child_profile():
    """Create mock child profile."""
    return _make_profile()


@pytest.fixture
def calendar(mock_api, mock_coordinator, child_profile):
    """Create a calendar instance."""
    return HuckleberryCalendar(mock_coordinator, child_profile, mock_api)


def test_calendar_attributes(calendar, child_profile):
    """Test calendar entity attributes."""
    assert calendar.unique_id == "test_child_uid_calendar"
    assert calendar.name == "Events"
    assert calendar._child is child_profile


@pytest.mark.asyncio
async def test_async_get_events(calendar, hass):
    """Test async get events integration."""
    calendar.hass = hass

    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() + timedelta(days=1)

    events = await calendar.async_get_events(hass, start_date, end_date)

    assert isinstance(events, list)
    assert len(events) == 0  # All mocked to return empty lists


def test_build_feed_events_splits_intervals(calendar):
    """Feed and bottle intervals should be split from one API response."""
    intervals = [
        FirebaseBreastFeedIntervalData(
            mode="breast",
            start=1700000000,
            lastSide="left",
            leftDuration=900,
            rightDuration=600,
            offset=0,
        ),
        FirebaseBottleFeedIntervalData(
            mode="bottle",
            start=1700000600,
            amount=120,
            units="ml",
            bottleType="Formula",
            offset=0,
        ),
    ]

    feed_events, bottle_events = HuckleberryCalendar._build_feed_events(intervals)

    assert len(feed_events) == 1
    assert len(bottle_events) == 1
    assert feed_events[0].summary.startswith("🍼 Feed")
    assert "L:15m" in feed_events[0].summary
    assert "R:10m" in feed_events[0].summary
    assert bottle_events[0].summary == "🍼 Bottle (120 ml)"


def test_build_feed_events_formats_feed_description(calendar):
    """Feed event descriptions should format seconds as min/sec text."""
    intervals = [
        FirebaseBreastFeedIntervalData(
            mode="breast",
            start=1700000000,
            lastSide="left",
            leftDuration=111,
            rightDuration=103,
            offset=0,
        ),
    ]

    feed_events, bottle_events = HuckleberryCalendar._build_feed_events(intervals)

    assert len(feed_events) == 1
    assert len(bottle_events) == 0
    assert "Feeding - Total: 3 min 34 sec" in (feed_events[0].description or "")
    assert "Left: 1 min 51 sec" in (feed_events[0].description or "")
    assert "Right: 1 min 43 sec" in (feed_events[0].description or "")


def test_build_feed_events_extracts_bottle_event(calendar):
    """Bottle intervals should render as bottle events."""
    intervals = [
        FirebaseBottleFeedIntervalData(
            mode="bottle",
            start=1700000600,
            amount=120,
            units="ml",
            bottleType="Formula",
            offset=0,
        ),
        FirebaseBreastFeedIntervalData(
            mode="breast",
            start=1700001200,
            lastSide="left",
            leftDuration=20,
            rightDuration=0,
            offset=0,
        ),
    ]

    feed_events, bottle_events = HuckleberryCalendar._build_feed_events(intervals)

    assert len(feed_events) == 1
    assert len(bottle_events) == 1
    assert bottle_events[0].summary == "🍼 Bottle (120 ml)"
    assert "Type: Formula" in (bottle_events[0].description or "")

"""Test calendar platform."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

from huckleberry_api.firebase_types import (
    FirebaseActivityIntervalData,
    FirebaseBottleFeedIntervalData,
    FirebaseBreastFeedIntervalData,
    FirebaseChildDocument,
    FirebasePumpIntervalData,
    FirebaseSolidsFeedIntervalData,
    FirebaseUserChildRef,
)

from custom_components.huckleberry.calendar import HuckleberryCalendar
from custom_components.huckleberry.models import HuckleberryChildProfile


def _make_profile(
    uid: str = "test_child_uid", name: str = "Test Baby"
) -> HuckleberryChildProfile:
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
    api.list_pump_intervals = AsyncMock(return_value=[])
    api.list_activity_intervals = AsyncMock(return_value=[])
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
    assert calendar._attr_translation_key == "events"
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
    intervals: list[
        FirebaseBreastFeedIntervalData
        | FirebaseBottleFeedIntervalData
        | FirebaseSolidsFeedIntervalData
    ] = [
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
    intervals: list[
        FirebaseBreastFeedIntervalData
        | FirebaseBottleFeedIntervalData
        | FirebaseSolidsFeedIntervalData
    ] = [
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
    intervals: list[
        FirebaseBreastFeedIntervalData
        | FirebaseBottleFeedIntervalData
        | FirebaseSolidsFeedIntervalData
    ] = [
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


def test_build_pump_events_includes_amounts_duration_and_notes():
    """Pumping history should retain its measurable details."""
    intervals = [
        FirebasePumpIntervalData(
            start=1700000000,
            entryMode="leftright",
            leftAmount=45,
            rightAmount=55,
            units="ml",
            offset=0,
            duration=600,
            notes="Stored for later",
        )
    ]

    events = HuckleberryCalendar._build_pump_events(intervals)

    assert len(events) == 1
    assert events[0].summary == "🤱 Pump (100 ml)"
    assert events[0].end - events[0].start == timedelta(minutes=10)
    assert "Left: 45 ml" in (events[0].description or "")
    assert "Right: 55 ml" in (events[0].description or "")
    assert "Stored for later" in (events[0].description or "")


@pytest.mark.parametrize(
    ("mode", "expected_label"),
    [
        ("bath", "Bath"),
        ("brushTeeth", "Brush Teeth"),
        ("indoorPlay", "Indoor Play"),
        ("outdoorPlay", "Outdoor Play"),
        ("screenTime", "Screen Time"),
        ("skinToSkin", "Skin-to-Skin"),
        ("storyTime", "Story Time"),
        ("tummyTime", "Tummy Time"),
    ],
)
def test_build_activity_events_covers_every_api_mode(mode, expected_label):
    """Every activity mode accepted by the API should produce one event."""
    intervals = [
        FirebaseActivityIntervalData(
            mode=mode,
            start=1700000000,
            offset=0,
            duration=300,
            notes="Activity note",
        )
    ]

    events = HuckleberryCalendar._build_activity_events(intervals)

    assert len(events) == 1
    assert expected_label in events[0].summary
    assert events[0].end - events[0].start == timedelta(minutes=5)
    assert "Activity note" in (events[0].description or "")


@pytest.mark.asyncio
async def test_activity_failure_preserves_other_calendar_history(
    calendar, mock_api, hass, caplog
):
    """A failed activity query must not discard other calendar categories."""
    mock_api.list_activity_intervals.side_effect = RuntimeError("activity unavailable")
    mock_api.list_pump_intervals.return_value = [
        FirebasePumpIntervalData(
            start=1700000000,
            entryMode="total",
            leftAmount=30,
            rightAmount=30,
            units="ml",
            offset=0,
        )
    ]
    calendar.hass = hass

    events = await calendar.async_get_events(
        hass,
        datetime.now() - timedelta(days=1),
        datetime.now() + timedelta(days=1),
    )

    assert len(events) == 1
    assert events[0].summary == "🤱 Pump (60 ml)"
    assert "Error fetching activity events" in caplog.text

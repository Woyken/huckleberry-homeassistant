"""Test calendar platform."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock
from zoneinfo import ZoneInfo

from homeassistant.util import dt as dt_util

from huckleberry_api.firebase_types import (
    FirebaseActivityIntervalData,
    FirebaseBottleFeedIntervalData,
    FirebaseBreastFeedIntervalData,
    FirebaseChildDocument,
    FirebaseDiaperData,
    FirebaseDiaperQuantity,
    FirebaseGrowthData,
    FirebaseMedicationData,
    FirebasePumpIntervalData,
    FirebaseSleepCondition,
    FirebaseSleepDetails,
    FirebaseSleepIntervalData,
    FirebaseSleepLocations,
    FirebaseSolidsFeedIntervalData,
    FirebaseTemperatureData,
    FirebaseUserChildRef,
    SolidsFoodEntry,
)

from custom_components.huckleberry.calendar import HuckleberryCalendar
from custom_components.huckleberry.features.calendar_events import (
    build_activity_events,
    build_diaper_events,
    build_feed_events,
    build_health_events,
    build_pump_events,
    build_sleep_events,
)
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

    feed_events, bottle_events = build_feed_events(intervals)

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

    feed_events, bottle_events = build_feed_events(intervals)

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

    feed_events, bottle_events = build_feed_events(intervals)

    assert len(feed_events) == 1
    assert len(bottle_events) == 1
    assert bottle_events[0].summary == "🍼 Bottle (120 ml)"
    assert "Type: Formula" in (bottle_events[0].description or "")


def test_build_feed_events_accepts_bottle_without_amount(calendar):
    """Bottle entries without a recorded volume should not show a made-up amount."""
    intervals = [
        FirebaseBottleFeedIntervalData(
            mode="bottle",
            start=1700000600,
            units="ml",
            bottleType="Formula",
            offset=0,
        ),
    ]

    feed_events, bottle_events = build_feed_events(intervals)

    assert feed_events == []
    assert len(bottle_events) == 1
    assert bottle_events[0].summary == "🍼 Bottle"
    assert bottle_events[0].description == "Bottle feeding\nType: Formula"


def test_build_sleep_events_includes_recorded_details(calendar):
    """Sleep details should be included in the calendar description."""
    intervals = [
        FirebaseSleepIntervalData(
            start=1700000000,
            duration=5400,
            offset=0,
            details=FirebaseSleepDetails(
                notes="Fell asleep in the stroller",
                startSleepCondition=FirebaseSleepCondition(happy=True),
                sleepLocations=FirebaseSleepLocations(stroller=True),
                endSleepCondition=FirebaseSleepCondition(upset=True),
            ),
        ),
    ]

    events = build_sleep_events(intervals)

    assert len(events) == 1
    assert events[0].summary == "💤 Sleep (1h 30m)"
    assert events[0].end - events[0].start == timedelta(minutes=90)
    description = events[0].description or ""
    assert "Sleep duration: 90 min" in description
    assert "Notes: Fell asleep in the stroller" in description
    assert "Start condition: Happy" in description
    assert "Sleep location: Stroller" in description
    assert "End condition: Upset" in description

def test_build_sleep_events_uses_absolute_end_time():
    """Sleep end times should follow absolute time across a DST change."""
    berlin = ZoneInfo("Europe/Berlin")
    original_time_zone = dt_util.DEFAULT_TIME_ZONE
    dt_util.DEFAULT_TIME_ZONE = berlin
    try:
        start = datetime(2026, 3, 29, 1, 30, tzinfo=berlin).timestamp()

        events = build_sleep_events(
            [FirebaseSleepIntervalData(start=start, duration=7200, offset=60)]
        )
    finally:
        dt_util.DEFAULT_TIME_ZONE = original_time_zone

    assert events[0].end.timestamp() - events[0].start.timestamp() == 7200
    assert events[0].end == datetime.fromtimestamp(start + 7200, tz=berlin)


def test_build_feed_events_includes_solids_details(calendar):
    """Solids events should show foods, reaction, and notes."""
    intervals = [
        FirebaseSolidsFeedIntervalData(
            mode="solids",
            start=1700000000,
            offset=0,
            foods={
                "banana": SolidsFoodEntry(
                    id="banana",
                    created_name="Banana",
                    source="curated",
                    amount="1/2",
                ),
            },
            reactions={"LOVED": True},
            notes="Ate everything",
        ),
    ]

    feed_events, bottle_events = build_feed_events(intervals)

    assert bottle_events == []
    assert len(feed_events) == 1
    assert feed_events[0].summary == "🥄 Solids (Banana (1/2))"
    description = feed_events[0].description or ""
    assert "Foods: Banana (1/2)" in description
    assert "Reaction: LOVED" in description
    assert "Notes: Ate everything" in description


def test_build_diaper_events_distinguishes_potty_and_details(calendar):
    """Potty entries share the diaper collection but should render as potty events."""
    intervals = [
        FirebaseDiaperData(
            mode="both",
            start=1700000000,
            offset=0,
            quantity=FirebaseDiaperQuantity(pee=50.0, poo=100.0),
            color="brown",
            consistency="solid",
            diaperRash=True,
            notes="After lunch",
            isPotty=True,
            howItHappened="wentPotty",
        ),
        FirebaseDiaperData(
            mode="pee",
            start=1700000600,
            offset=0,
        ),
    ]

    events = build_diaper_events(intervals)

    assert len(events) == 2
    assert events[0].summary == "🚽 Potty (Both, Went potty)"
    description = events[0].description or ""
    assert "Potty: both" in description
    assert "How it happened: Went potty" in description
    assert "Pee amount: medium" in description
    assert "Poo amount: big" in description
    assert "Color: brown" in description
    assert "Consistency: solid" in description
    assert "Diaper rash: yes" in description
    assert "Notes: After lunch" in description
    assert events[1].summary == "💧 Diaper (Pee)"


def test_build_health_events_covers_all_health_entry_types(calendar):
    """Growth, medication, and temperature entries should all be rendered."""
    entries = [
        FirebaseGrowthData(
            mode="growth",
            start=1700000000,
            offset=0,
            weight=5.2,
            weightUnits="kg",
            height=60,
            heightUnits="cm",
            head=40,
            headUnits="hcm",
        ),
        FirebaseMedicationData(
            mode="medication",
            start=1700000600,
            offset=0,
            medication_id="med_1",
            medication_name="Vitamin D",
            amount=1.0,
            units="ml",
            notes="After breakfast",
        ),
        FirebaseTemperatureData(
            mode="temperature",
            start=1700001200,
            offset=0,
            amount=37.2,
            units="C",
            notes="Slight fever",
        ),
    ]

    events = build_health_events(entries)

    assert [event.summary for event in events] == [
        "📏 Growth Measurement",
        "💊 Medication (Vitamin D)",
        "🌡️ Temperature",
    ]
    growth_description = events[0].description or ""
    assert "Weight: 5.2 kg" in growth_description
    assert "Height: 60 cm" in growth_description
    assert "Head: 40 cm" in growth_description
    medication_description = events[1].description or ""
    assert "Medication: Vitamin D" in medication_description
    assert "Amount: 1 ml" in medication_description
    assert "Notes: After breakfast" in medication_description
    temperature_description = events[2].description or ""
    assert "Temperature: 37.2 °C" in temperature_description
    assert "Notes: Slight fever" in temperature_description


def test_build_pump_events(calendar):
    """Pump entries should show amounts, duration, and notes."""
    intervals = [
        FirebasePumpIntervalData(
            start=1700000000,
            entryMode="leftright",
            leftAmount=60,
            rightAmount=55,
            units="ml",
            offset=0,
            duration=900,
            notes="Morning pump",
        ),
        FirebasePumpIntervalData(
            start=1700003600,
            entryMode="total",
            leftAmount=50,
            rightAmount=50,
            units="ml",
            offset=0,
        ),
    ]

    events = build_pump_events(intervals)

    assert len(events) == 2
    assert events[0].summary == "🍼 Pump (15m · 115 ml)"
    assert events[0].end - events[0].start == timedelta(minutes=15)
    description = events[0].description or ""
    assert "Left: 60 ml" in description
    assert "Right: 55 ml" in description
    assert "Total: 115 ml" in description
    assert "Duration: 15 min" in description
    assert "Notes: Morning pump" in description
    assert events[1].summary == "🍼 Pump (100 ml)"
    assert events[1].end == events[1].start
    assert "Total: 100 ml" in (events[1].description or "")
    assert "Left:" not in (events[1].description or "")


def test_build_activity_events(calendar):
    """Activity entries should use readable labels and include duration and notes."""
    intervals = [
        FirebaseActivityIntervalData(
            mode="tummyTime",
            start=1700000000,
            offset=0,
            duration=300,
            notes="Play mat",
        ),
        FirebaseActivityIntervalData(
            mode="bath",
            start=1700003600,
            offset=0,
        ),
    ]

    events = build_activity_events(intervals)

    assert len(events) == 2
    assert events[0].summary == "🧸 Tummy Time (5m)"
    assert events[0].end - events[0].start == timedelta(minutes=5)
    description = events[0].description or ""
    assert "Activity: Tummy Time" in description
    assert "Duration: 5 min" in description
    assert "Notes: Play mat" in description
    assert events[1].summary == "🛁 Bath"
    assert events[1].end == events[1].start


@pytest.mark.asyncio
async def test_async_get_events_includes_pump_and_activity(
    calendar, mock_api, hass
):
    """The calendar should fetch every history type supported by the API."""
    calendar.hass = hass
    mock_api.list_pump_intervals.return_value = [
        FirebasePumpIntervalData(
            start=1700000000,
            entryMode="total",
            leftAmount=50,
            rightAmount=50,
            units="ml",
            offset=0,
        )
    ]
    mock_api.list_activity_intervals.return_value = [
        FirebaseActivityIntervalData(
            mode="tummyTime",
            start=1700000600,
            offset=0,
            duration=300,
        )
    ]

    events = await calendar.async_get_events(
        hass,
        datetime.fromtimestamp(1699990000),
        datetime.fromtimestamp(1700010000),
    )

    assert [event.summary for event in events] == [
        "🍼 Pump (100 ml)",
        "🧸 Tummy Time (5m)",
    ]

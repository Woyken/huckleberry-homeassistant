"""Tests for Huckleberry daily statistics sensors."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from huckleberry_api.firebase_types import (
    FirebaseBottleFeedIntervalData,
    FirebaseBreastFeedIntervalData,
    FirebaseDiaperData,
    FirebaseDiaperQuantity,
    FirebaseSleepIntervalData,
    FirebaseSolidsFeedIntervalData,
)

from custom_components.huckleberry.const import DOMAIN


def _make_diaper(mode: str, start: float = 1716800000.0) -> FirebaseDiaperData:
    """Build a minimal diaper interval."""
    return FirebaseDiaperData(mode=mode, start=start, offset=36000)


def _make_bottle(
    amount: float = 120.0, units: str = "ml", start: float = 1716800000.0
) -> FirebaseBottleFeedIntervalData:
    """Build a minimal bottle interval."""
    return FirebaseBottleFeedIntervalData(
        mode="bottle",
        start=start,
        bottleType="Formula",
        amount=amount,
        units=units,
        offset=36000,
    )


def _make_nursing(
    left: float = 300.0, right: float = 240.0, start: float = 1716800000.0
) -> FirebaseBreastFeedIntervalData:
    """Build a minimal breast feed interval."""
    return FirebaseBreastFeedIntervalData(
        mode="breast",
        start=start,
        lastSide="left",
        leftDuration=left,
        rightDuration=right,
        offset=36000,
    )


def _make_sleep(
    duration: float = 3600.0, start: float = 1716800000.0
) -> FirebaseSleepIntervalData:
    """Build a minimal sleep interval."""
    return FirebaseSleepIntervalData(
        start=start,
        duration=duration,
        offset=36000,
    )


def _make_solids(start: float = 1716800000.0) -> FirebaseSolidsFeedIntervalData:
    """Build a minimal solids interval."""
    return FirebaseSolidsFeedIntervalData(
        mode="solids",
        start=start,
        offset=36000,
    )


async def _setup_integration(
    hass: HomeAssistant,
    mock_api,
    *,
    diapers: list | None = None,
    feeds: list | None = None,
    sleeps: list | None = None,
):
    """Set up the integration with optional interval data."""
    mock_api.list_diaper_intervals = AsyncMock(return_value=diapers or [])
    mock_api.list_feed_intervals = AsyncMock(return_value=feeds or [])
    mock_api.list_sleep_intervals = AsyncMock(return_value=sleeps or [])

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_api,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry


async def test_statistics_sensors_no_data(hass: HomeAssistant, mock_huckleberry_api):
    """Test statistics sensors show 0 when no intervals exist."""
    await _setup_integration(hass, mock_huckleberry_api)

    diapers = hass.states.get("sensor.test_child_diapers_today")
    assert diapers is not None
    assert diapers.state == "0"

    bottles = hass.states.get("sensor.test_child_bottles_today")
    assert bottles is not None
    assert bottles.state == "0"

    nursing = hass.states.get("sensor.test_child_nursing_today")
    assert nursing is not None
    assert nursing.state == "0"

    sleep = hass.states.get("sensor.test_child_sleep_today")
    assert sleep is not None
    assert sleep.state == "0"


async def test_diaper_counts(hass: HomeAssistant, mock_huckleberry_api):
    """Test diaper sensor counts by type."""
    diapers = [
        _make_diaper("pee", 1716800100.0),
        _make_diaper("poo", 1716800200.0),
        _make_diaper("both", 1716800300.0),
        _make_diaper("pee", 1716800400.0),
        _make_diaper("dry", 1716800500.0),
    ]
    await _setup_integration(hass, mock_huckleberry_api, diapers=diapers)

    state = hass.states.get("sensor.test_child_diapers_today")
    assert state is not None
    assert state.state == "5"
    assert state.attributes["pee_only"] == 2
    assert state.attributes["poo_only"] == 1
    assert state.attributes["mixed"] == 1


async def test_bottle_totals(hass: HomeAssistant, mock_huckleberry_api):
    """Test bottle sensor counts and total ml."""
    feeds = [
        _make_bottle(120.0, "ml", 1716800100.0),
        _make_bottle(90.0, "ml", 1716800200.0),
        _make_bottle(4.0, "oz", 1716800300.0),  # ~118.3 ml
    ]
    await _setup_integration(hass, mock_huckleberry_api, feeds=feeds)

    state = hass.states.get("sensor.test_child_bottles_today")
    assert state is not None
    assert state.state == "3"
    total_ml = state.attributes["total_ml"]
    assert 328.0 < total_ml < 329.0  # 120 + 90 + 118.3


async def test_nursing_totals(hass: HomeAssistant, mock_huckleberry_api):
    """Test nursing sensor counts and total duration."""
    feeds = [
        _make_nursing(300.0, 240.0, 1716800100.0),  # 9 min
        _make_nursing(420.0, 0.0, 1716800200.0),  # 7 min
    ]
    await _setup_integration(hass, mock_huckleberry_api, feeds=feeds)

    state = hass.states.get("sensor.test_child_nursing_today")
    assert state is not None
    assert state.state == "2"
    assert state.attributes["total_minutes"] == 16  # (540 + 420) // 60
    assert state.attributes["total_duration"] == "16m"


async def test_sleep_totals(hass: HomeAssistant, mock_huckleberry_api):
    """Test sleep sensor counts and total duration."""
    sleeps = [
        _make_sleep(3600.0, 1716800100.0),  # 1h
        _make_sleep(2700.0, 1716800200.0),  # 45m
        _make_sleep(5400.0, 1716800300.0),  # 1h 30m
    ]
    await _setup_integration(hass, mock_huckleberry_api, sleeps=sleeps)

    state = hass.states.get("sensor.test_child_sleep_today")
    assert state is not None
    assert state.state == "3"
    assert state.attributes["total_minutes"] == 195  # (3600+2700+5400) // 60
    assert state.attributes["total_duration"] == "3h 15m"


async def test_mixed_feed_types(hass: HomeAssistant, mock_huckleberry_api):
    """Test that bottles, nursing, and solids all count correctly together."""
    feeds = [
        _make_bottle(120.0, "ml", 1716800100.0),
        _make_nursing(300.0, 300.0, 1716800200.0),
        _make_solids(1716800300.0),
        _make_bottle(90.0, "ml", 1716800400.0),
    ]
    await _setup_integration(hass, mock_huckleberry_api, feeds=feeds)

    bottles = hass.states.get("sensor.test_child_bottles_today")
    assert bottles is not None
    assert bottles.state == "2"
    assert bottles.attributes["total_ml"] == 210.0

    nursing = hass.states.get("sensor.test_child_nursing_today")
    assert nursing is not None
    assert nursing.state == "1"


async def test_statistics_api_called_with_timestamps(
    hass: HomeAssistant, mock_huckleberry_api
):
    """Test that the coordinator passes integer timestamps to list APIs."""
    await _setup_integration(hass, mock_huckleberry_api)

    # Verify the APIs were called (they are called during first refresh)
    mock_huckleberry_api.list_diaper_intervals.assert_called()
    call_args = mock_huckleberry_api.list_diaper_intervals.call_args
    # Arguments should be (child_uid, start_ts, end_ts)
    assert call_args[0][0] == "child_1"
    assert isinstance(call_args[0][1], int)
    assert isinstance(call_args[0][2], int)
    assert call_args[0][1] < call_args[0][2]

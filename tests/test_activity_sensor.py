"""Test activity sensors."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from huckleberry_api.firebase_types import (
    FirebaseActivityDocumentData,
    FirebaseActivityPrefs,
    FirebaseActivityTimerData,
    FirebaseActivityTimerEntryData,
    FirebaseLastActivityData,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.huckleberry.const import DOMAIN

LAST_ACTIVITY_ENTITIES = {
    "bath": "sensor.test_child_bath",
    "brush_teeth": "sensor.test_child_brush_teeth",
    "indoor_play": "sensor.test_child_indoor_play",
    "outdoor_play": "sensor.test_child_outdoor_play",
    "screen_time": "sensor.test_child_screen_time",
    "skin_to_skin": "sensor.test_child_skin_to_skin",
    "story_time": "sensor.test_child_story_time",
    "tummy_time": "sensor.test_child_tummy_time",
}


def _expected_time(timestamp: int) -> str:
    """Return the Home Assistant timestamp string for a unix timestamp."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


@pytest.fixture
async def activity_callback(hass: HomeAssistant, mock_huckleberry_api):
    """Set up sensors and return the child's activity listener callback."""
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
        return_value=mock_huckleberry_api,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return mock_huckleberry_api.setup_activity_listener.call_args.args[1]


async def test_activity_last_sensors(hass: HomeAssistant, activity_callback):
    """Last activity sensors expose the completed session for each mode."""
    activity_callback(
        FirebaseActivityDocumentData(
            prefs=FirebaseActivityPrefs(
                lastBath=FirebaseLastActivityData(start=1700000000, duration=300),
                lastTummyTime=FirebaseLastActivityData(start=1700003600, duration=120),
            ),
        )
    )
    await hass.async_block_till_done()

    bath = hass.states.get(LAST_ACTIVITY_ENTITIES["bath"])
    assert bath is not None
    assert bath.state == _expected_time(1700000000)
    assert bath.attributes["device_class"] == "timestamp"
    assert bath.attributes["time"] == _expected_time(1700000000)
    assert bath.attributes["duration"] == "PT5M"

    tummy_time = hass.states.get(LAST_ACTIVITY_ENTITIES["tummy_time"])
    assert tummy_time is not None
    assert tummy_time.state == _expected_time(1700003600)
    assert tummy_time.attributes["time"] == _expected_time(1700003600)
    assert tummy_time.attributes["duration"] == "PT2M"

    story_time = hass.states.get(LAST_ACTIVITY_ENTITIES["story_time"])
    assert story_time is not None
    assert story_time.state == "unknown"
    assert "time" not in story_time.attributes
    assert "duration" not in story_time.attributes

    registry_entry = er.async_get(hass).async_get(LAST_ACTIVITY_ENTITIES["bath"])
    assert registry_entry is not None
    assert registry_entry.unique_id == "child_1_activity_bath"


@pytest.mark.parametrize(
    "activities",
    [
        FirebaseActivityDocumentData(),
        FirebaseActivityDocumentData(prefs=FirebaseActivityPrefs()),
        FirebaseActivityDocumentData(
            prefs=FirebaseActivityPrefs(lastBath=FirebaseLastActivityData())
        ),
    ],
)
async def test_activity_last_sensor_missing_data(
    hass: HomeAssistant,
    activity_callback,
    activities: FirebaseActivityDocumentData,
):
    """Missing activity data leaves the last sensors unknown."""
    activity_callback(activities)
    await hass.async_block_till_done()

    for entity_id in LAST_ACTIVITY_ENTITIES.values():
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unknown"
        assert "time" not in state.attributes
        assert "duration" not in state.attributes


@pytest.mark.parametrize(
    ("timer", "expected_state"),
    [
        (None, "unknown"),
        (
            FirebaseActivityTimerData(
                bath=FirebaseActivityTimerEntryData(
                    active=False,
                    startTime=1700000000000,
                    uuid="session",
                )
            ),
            "none",
        ),
        (
            FirebaseActivityTimerData(
                bath=FirebaseActivityTimerEntryData(
                    active=True,
                    paused=False,
                    startTime=1700000000000,
                    uuid="session",
                )
            ),
            "active",
        ),
        (
            FirebaseActivityTimerData(
                bath=FirebaseActivityTimerEntryData(
                    active=True,
                    paused=True,
                    startTime=1700000000000,
                    endTime=1700000300000,
                    uuid="session",
                )
            ),
            "paused",
        ),
    ],
)
async def test_activity_timer_sensor_state(
    hass: HomeAssistant,
    activity_callback,
    timer: FirebaseActivityTimerData | None,
    expected_state: str,
):
    """The shared activity timer exposes the active session state."""
    activity_callback(FirebaseActivityDocumentData(timer=timer))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_activity")
    assert state is not None
    assert state.state == expected_state
    assert state.attributes["device_class"] == "enum"

    if expected_state == "active":
        assert state.attributes["current_mode"] == "Bath"
        assert state.attributes["current_start"] == _expected_time(1700000000)
        assert "current_end" not in state.attributes
    elif expected_state == "paused":
        assert state.attributes["current_mode"] == "Bath"
        assert state.attributes["current_start"] == _expected_time(1700000000)
        assert state.attributes["current_end"] == _expected_time(1700000300)
    else:
        assert "current_mode" not in state.attributes
        assert "current_start" not in state.attributes
        assert "current_end" not in state.attributes


async def test_activity_timer_sensor_previous_session(
    hass: HomeAssistant,
    activity_callback,
):
    """The timer sensor reports the most recently completed activity."""
    activity_callback(
        FirebaseActivityDocumentData(
            timer=FirebaseActivityTimerData(
                bath=FirebaseActivityTimerEntryData(
                    active=False,
                    startTime=1700000000000,
                    uuid="session",
                )
            ),
            prefs=FirebaseActivityPrefs(
                lastBath=FirebaseLastActivityData(start=1700000000, duration=300),
                lastTummyTime=FirebaseLastActivityData(
                    start=1700003600,
                    duration=120,
                ),
            ),
        )
    )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_activity")
    assert state is not None
    assert state.state == "none"
    assert state.attributes["previous_mode"] == "Tummy Time"
    assert state.attributes["previous_start"] == _expected_time(1700003600)
    assert state.attributes["previous_duration"] == "PT2M"


async def test_activity_sensors_multiple_children(
    hass: HomeAssistant,
    mock_huckleberry_api_multiple_children,
):
    """Each child gets independent activity sensors and listener callbacks."""
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
        return_value=mock_huckleberry_api_multiple_children,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert mock_huckleberry_api_multiple_children.setup_activity_listener.await_count == 3

    for child in ("first_child", "second_child", "third_child"):
        for entity in (
            "activity",
            "bath",
            "brush_teeth",
            "indoor_play",
            "outdoor_play",
            "screen_time",
            "skin_to_skin",
            "story_time",
            "tummy_time",
        ):
            assert hass.states.get(f"sensor.{child}_{entity}") is not None

    first_callback = (
        mock_huckleberry_api_multiple_children.setup_activity_listener.call_args_list[
            0
        ].args[1]
    )
    second_callback = (
        mock_huckleberry_api_multiple_children.setup_activity_listener.call_args_list[
            1
        ].args[1]
    )
    first_callback(
        FirebaseActivityDocumentData(
            prefs=FirebaseActivityPrefs(
                lastBath=FirebaseLastActivityData(start=1700000000, duration=300),
            ),
        )
    )
    second_callback(
        FirebaseActivityDocumentData(
            prefs=FirebaseActivityPrefs(
                lastTummyTime=FirebaseLastActivityData(
                    start=1700003600,
                    duration=120,
                ),
            ),
        )
    )
    await hass.async_block_till_done()

    assert hass.states.get("sensor.first_child_bath").state == _expected_time(
        1700000000
    )
    assert hass.states.get("sensor.first_child_tummy_time").state == "unknown"
    assert hass.states.get("sensor.second_child_tummy_time").state == _expected_time(
        1700003600
    )
    assert hass.states.get("sensor.second_child_bath").state == "unknown"
    assert hass.states.get("sensor.third_child_bath").state == "unknown"

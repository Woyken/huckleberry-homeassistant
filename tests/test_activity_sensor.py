"""Test activity sensors."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler
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
    """Last activity sensors appear for modes with a completed session."""
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

    assert hass.states.get(LAST_ACTIVITY_ENTITIES["story_time"]) is None

    registry = er.async_get(hass)
    bath_registry = registry.async_get(LAST_ACTIVITY_ENTITIES["bath"])
    assert bath_registry is not None
    assert bath_registry.unique_id == "child_1_activity_bath"
    assert bath_registry.disabled_by is None

    story_time_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "child_1_activity_story_time"
    )
    assert story_time_id is not None
    story_time_registry = registry.async_get(story_time_id)
    assert story_time_registry is not None
    assert story_time_registry.disabled_by is RegistryEntryDisabler.INTEGRATION


async def test_activity_sensors_hidden_without_data(
    hass: HomeAssistant,
    activity_callback,
):
    """Modes without a session stay disabled, while the timer sensor is visible."""
    activity_callback(
        FirebaseActivityDocumentData(
            prefs=FirebaseActivityPrefs(
                lastBath=FirebaseLastActivityData(),
            ),
        )
    )
    await hass.async_block_till_done()

    for entity_id in LAST_ACTIVITY_ENTITIES.values():
        assert hass.states.get(entity_id) is None

    timer_state = hass.states.get("sensor.test_child_activity")
    assert timer_state is not None
    assert timer_state.state == "unknown"

    registry = er.async_get(hass)
    for mode in LAST_ACTIVITY_ENTITIES:
        unique_id = f"child_1_activity_{mode}"
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None
        registry_entry = registry.async_get(entity_id)
        assert registry_entry is not None
        assert registry_entry.disabled_by is RegistryEntryDisabler.INTEGRATION


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


async def test_activity_timer_previous_session_uses_completion_time(
    hass: HomeAssistant,
    activity_callback,
):
    """A long session that ends later wins over a shorter, later start."""
    activity_callback(
        FirebaseActivityDocumentData(
            prefs=FirebaseActivityPrefs(
                lastBath=FirebaseLastActivityData(start=1700000000, duration=3600),
                lastStoryTime=FirebaseLastActivityData(
                    start=1700001800,
                    duration=300,
                ),
            ),
        )
    )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_activity")
    assert state is not None
    assert state.attributes["previous_mode"] == "Bath"
    assert state.attributes["previous_start"] == _expected_time(1700000000)
    assert state.attributes["previous_duration"] == "PT1H"


async def test_user_disabled_activity_sensor_stays_disabled(
    hass: HomeAssistant,
    activity_callback,
):
    """A sensor disabled by the user is not enabled when a session appears."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "child_1_activity_bath"
    )
    assert entity_id is not None
    registry.async_update_entity(entity_id, disabled_by=RegistryEntryDisabler.USER)

    activity_callback(
        FirebaseActivityDocumentData(
            prefs=FirebaseActivityPrefs(
                lastBath=FirebaseLastActivityData(start=1700000000, duration=300),
            ),
        )
    )
    await hass.async_block_till_done()

    assert hass.states.get(LAST_ACTIVITY_ENTITIES["bath"]) is None
    registry_entry = registry.async_get(entity_id)
    assert registry_entry is not None
    assert registry_entry.disabled_by is RegistryEntryDisabler.USER


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
        assert hass.states.get(f"sensor.{child}_activity") is not None
        assert hass.states.get(f"sensor.{child}_bath") is None

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
    assert hass.states.get("sensor.first_child_tummy_time") is None
    assert hass.states.get("sensor.second_child_tummy_time").state == _expected_time(
        1700003600
    )
    assert hass.states.get("sensor.second_child_bath") is None
    assert hass.states.get("sensor.third_child_bath") is None

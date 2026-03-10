"""Test Huckleberry sleep and nursing sensors."""
from datetime import datetime, timezone
from unittest.mock import patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from huckleberry_api.firebase_types import (
    FirebaseFeedDocumentData,
    FirebaseFeedTimerData,
    FirebaseSleepDocumentData,
    FirebaseSleepTimerData,
    FirebaseTimestamp,
)

from custom_components.huckleberry.const import DOMAIN


async def test_sleep_feed_sensors(hass: HomeAssistant, mock_huckleberry_api):
    """Test sleep and nursing sensors."""
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
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Get the coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Simulate sleep data update (Active)
    coordinator._realtime_data["child_1"].sleep_status = FirebaseSleepDocumentData(
        timer=FirebaseSleepTimerData(
            active=True,
            paused=False,
            timestamp=FirebaseTimestamp(seconds=1700000000),
            timerStartTime=1700000000000,
            uuid="t1",
        ),
    )
    coordinator._realtime_data["child_1"].feed_status = FirebaseFeedDocumentData(
        timer=FirebaseFeedTimerData(
            active=True,
            paused=False,
            feedStartTime=1700000100,
            lastSide="left",
            uuid="t2",
        ),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    # Check sleep sensor
    state = hass.states.get("sensor.test_child_sleep")
    assert state is not None
    assert state.state == "active"
    assert state.attributes.get("current_start") == datetime.fromtimestamp(1700000000, tz=timezone.utc).isoformat()

    # Check nursing sensor.
    state = hass.states.get("sensor.test_child_nursing")
    assert state is not None
    assert state.state == "active"
    assert state.attributes.get("current_last_side") == "Left"
    assert state.attributes.get("current_start") == datetime.fromtimestamp(1700000100, tz=timezone.utc).isoformat()

    # Simulate Paused
    coordinator._realtime_data["child_1"].sleep_status = FirebaseSleepDocumentData(
        timer=FirebaseSleepTimerData(
            active=True,
            paused=True,
            timerStartTime=1700000000000,
            timerEndTime=1700000300000,
            uuid="t1",
        ),
    )
    coordinator._realtime_data["child_1"].feed_status = FirebaseFeedDocumentData(
        timer=FirebaseFeedTimerData(active=True, paused=True, lastSide="left", uuid="t2"),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_sleep")
    assert state.state == "paused"
    assert state.attributes.get("current_start") == datetime.fromtimestamp(1700000000, tz=timezone.utc).isoformat()
    assert state.attributes.get("current_end") == datetime.fromtimestamp(1700000300, tz=timezone.utc).isoformat()

    state = hass.states.get("sensor.test_child_nursing")
    assert state.state == "paused"

    # Simulate Inactive (None)
    coordinator._realtime_data["child_1"].sleep_status = FirebaseSleepDocumentData(
        timer=FirebaseSleepTimerData(active=False, paused=False, uuid="t1"),
    )
    coordinator._realtime_data["child_1"].feed_status = FirebaseFeedDocumentData(
        timer=FirebaseFeedTimerData(active=False, paused=False, uuid="t2"),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_sleep")
    assert state.state == "none"

    state = hass.states.get("sensor.test_child_nursing")
    assert state.state == "none"

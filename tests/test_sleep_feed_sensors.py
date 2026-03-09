"""Test Huckleberry sleep and feeding sensors."""
from unittest.mock import patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from huckleberry_api.firebase_types import (
    FirebaseFeedDocumentData,
    FirebaseFeedTimerData,
    FirebaseSleepDocumentData,
    FirebaseSleepTimerData,
)

from custom_components.huckleberry.const import DOMAIN


async def test_sleep_feed_sensors(hass: HomeAssistant, mock_huckleberry_api):
    """Test sleep and feeding sensors."""
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
        timer=FirebaseSleepTimerData(active=True, paused=False, uuid="t1"),
    )
    coordinator._realtime_data["child_1"].feed_status = FirebaseFeedDocumentData(
        timer=FirebaseFeedTimerData(active=True, paused=False, lastSide="left", uuid="t2"),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    # Check sleep sensor
    state = hass.states.get("sensor.test_child_sleep_status")
    assert state is not None
    assert state.state == "sleeping"

    # Check feeding sensor
    state = hass.states.get("sensor.test_child_feeding_status")
    assert state is not None
    assert state.state == "feeding"
    assert state.attributes.get("last_side") == "left"

    # Simulate Paused
    coordinator._realtime_data["child_1"].sleep_status = FirebaseSleepDocumentData(
        timer=FirebaseSleepTimerData(active=True, paused=True, uuid="t1"),
    )
    coordinator._realtime_data["child_1"].feed_status = FirebaseFeedDocumentData(
        timer=FirebaseFeedTimerData(active=True, paused=True, lastSide="left", uuid="t2"),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_sleep_status")
    assert state.state == "paused"

    state = hass.states.get("sensor.test_child_feeding_status")
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

    state = hass.states.get("sensor.test_child_sleep_status")
    assert state.state == "none"

    state = hass.states.get("sensor.test_child_feeding_status")
    assert state.state == "none"

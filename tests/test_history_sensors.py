"""Test Huckleberry history attributes on current sensors."""
from unittest.mock import patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from datetime import datetime, timezone

from huckleberry_api.firebase_types import (
    FirebaseFeedDocumentData,
    FirebaseFeedPrefs,
    FirebaseFeedTimerData,
    FirebaseLastNursingData,
    FirebaseLastSideData,
    FirebaseLastSleepData,
    FirebaseSleepDocumentData,
    FirebaseSleepPrefs,
    FirebaseSleepTimerData,
)

from custom_components.huckleberry.const import DOMAIN


async def test_history_sensors(hass: HomeAssistant, mock_huckleberry_api):
    """Test historical attributes on the sleep and nursing sensors."""
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

    # Scenario A: Active nursing on the left side.
    coordinator._realtime_data["child_1"].feed_status = FirebaseFeedDocumentData(
        timer=FirebaseFeedTimerData(
            active=True, paused=False, activeSide="left", lastSide="none", uuid="t1",
        ),
    )
    coordinator._realtime_data["child_1"].sleep_status = FirebaseSleepDocumentData(
        timer=FirebaseSleepTimerData(active=False, paused=False, uuid="t2"),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_nursing")
    assert state is not None
    assert state.state == "active"
    assert state.attributes["current_active_side"] == "Left"

    # Scenario B: Paused nursing where the right side was last active.
    coordinator._realtime_data["child_1"].feed_status = FirebaseFeedDocumentData(
        timer=FirebaseFeedTimerData(
            active=True, paused=True, lastSide="right", uuid="t1",
        ),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_nursing")
    assert state is not None
    assert state.state == "paused"

    # Scenario C: Inactive nursing with historical data.
    coordinator._realtime_data["child_1"].feed_status = FirebaseFeedDocumentData(
        timer=FirebaseFeedTimerData(active=False, paused=False, uuid="t1"),
        prefs=FirebaseFeedPrefs(
            lastSide=FirebaseLastSideData(start=1700000000, lastSide="left"),
            lastNursing=FirebaseLastNursingData(
                start=1700000000,
                duration=600,
                leftDuration=300,
                rightDuration=300,
            ),
        ),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_nursing")
    assert state is not None
    assert state.state == "none"
    assert state.attributes["previous_start"] == datetime.fromtimestamp(1700000000, tz=timezone.utc).isoformat()
    assert state.attributes["previous_duration"] == "PT10M"
    assert state.attributes["previous_left_duration"] == "PT5M"
    assert state.attributes["previous_right_duration"] == "PT5M"
    assert state.attributes["previous_last_side"] == "Left"

    # Sleep history is exposed on the current sleep sensor.
    coordinator._realtime_data["child_1"].sleep_status = FirebaseSleepDocumentData(
        timer=FirebaseSleepTimerData(active=False, paused=False, uuid="t2"),
        prefs=FirebaseSleepPrefs(
            lastSleep=FirebaseLastSleepData(
                start=1700001000,
                duration=3600,  # 1 hour
            ),
        ),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_sleep")
    assert state is not None
    assert state.state == "none"
    assert state.attributes["previous_start"] == datetime.fromtimestamp(1700001000, tz=timezone.utc).isoformat()
    assert state.attributes["previous_duration"] == "PT1H"

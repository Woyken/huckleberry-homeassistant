"""Test Huckleberry history and previous event sensors."""
from unittest.mock import patch
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from custom_components.huckleberry.const import DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from datetime import datetime, timezone

async def test_history_sensors(hass: HomeAssistant, mock_huckleberry_api):
    """Test history sensors (Last Side, Previous Sleep/Feed)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
    )
    entry.add_to_hass(hass)

    # Mock coordinator data
    mock_huckleberry_api.get_children.return_value = [
        {
            "uid": "child_1",
            "name": "Test Child",
            "birthDate": "2023-01-01",
            "gender": "boy",
            "profilePictureUrl": None
        }
    ]

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Get the coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # 1. Test Last Feeding Side Sensor
    # Scenario A: Active Feeding (Left)
    coordinator._realtime_data = {
        "child_1": {
            "feed_status": {
                "timer": {
                    "active": True,
                    "paused": False,
                    "activeSide": "left",
                    "lastSide": "none"
                },
                "prefs": {}
            },
            "sleep_status": {"timer": {}, "prefs": {}}
        }
    }
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_last_feeding_side")
    assert state.state == "Left"

    # Scenario B: Paused Feeding (Right was active)
    coordinator._realtime_data["child_1"]["feed_status"]["timer"] = {
        "active": True,
        "paused": True,
        # activeSide is removed on pause
        "lastSide": "right" # pause_feeding sets lastSide = current_side
    }
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_last_feeding_side")
    assert state.state == "Right"

    # Scenario C: Stopped Feeding (History)
    coordinator._realtime_data["child_1"]["feed_status"] = {
        "timer": {"active": False},
        "prefs": {
            "lastSide": {"lastSide": "left"},
            "lastNursing": {
                "start": 1700000000,
                "duration": 600,
                "leftDuration": 300,
                "rightDuration": 300
            }
        }
    }
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_child_last_feeding_side")
    assert state.state == "Left"

    # 2. Test Previous Feed Sensor
    state = hass.states.get("sensor.test_child_previous_feed_start")
    assert state.state == datetime.fromtimestamp(1700000000, tz=timezone.utc).isoformat()
    assert state.attributes["duration_seconds"] == 600
    assert state.attributes["left_duration_seconds"] == 300
    assert state.attributes["right_duration_seconds"] == 300
    assert state.attributes["last_side"] == "left"

    # 3. Test Previous Sleep Sensors
    coordinator._realtime_data["child_1"]["sleep_status"] = {
        "timer": {"active": False},
        "prefs": {
            "lastSleep": {
                "start": 1700001000,
                "duration": 3600 # 1 hour
            }
        }
    }
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    # Start Sensor
    state = hass.states.get("sensor.test_child_previous_sleep_start")
    assert state.state == datetime.fromtimestamp(1700001000, tz=timezone.utc).isoformat()
    assert state.attributes["duration_seconds"] == 3600
    assert state.attributes["duration"] == "1h 0m"

    # End Sensor
    state = hass.states.get("sensor.test_child_previous_sleep_end")
    # End = Start + Duration = 1700001000 + 3600 = 1700004600
    assert state.state == datetime.fromtimestamp(1700004600, tz=timezone.utc).isoformat()
    assert state.attributes["duration_seconds"] == 3600

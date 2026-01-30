"""Test Huckleberry sensors."""
from unittest.mock import patch, MagicMock
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from custom_components.huckleberry.const import DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_sensors(hass: HomeAssistant, mock_huckleberry_api):
    """Test sensors."""
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

    # Simulate growth data
    coordinator._realtime_data = {
        "child_1": {
            "growth_data": {
                "weight": 10.5,
                "height": 75.0,
                "head": 45.0,
                "weight_units": "kg",
                "height_units": "cm",
                "head_units": "hcm",
                "timestamp": 1234567890
            },
            "diaper_data": {
                "prefs": {
                    "lastDiaper": {
                        "mode": "pee",
                        "start": 1234567890
                    }
                }
            }
        }
    }
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    # Check children count sensor
    state = hass.states.get("sensor.huckleberry_children")
    assert state.state == "1"
    assert state.attributes["children"][0]["name"] == "Test Child"

    # Check child profile sensor
    state = hass.states.get("sensor.test_child_profile")
    assert state.state == "Test Child"
    assert state.attributes["birthday"] == "2023-01-01"

    # Check growth sensor
    state = hass.states.get("sensor.test_child_growth")
    from datetime import datetime
    expected_date = datetime.fromtimestamp(1234567890).strftime("%Y-%m-%d %H:%M")
    assert state.state == expected_date
    assert state.attributes["weight"] == 10.5
    assert state.attributes["height"] == 75.0

    # Check diaper sensor
    state = hass.states.get("sensor.test_child_last_diaper")
    assert state is not None
    # The sensor returns formatted date, let's just check it's not "No changes logged"
    assert state.state != "No changes logged"
    assert state.attributes["mode"] == "pee"
    assert state.attributes["timestamp"] == 1234567890

async def test_bottle_sensor(hass: HomeAssistant, mock_huckleberry_api):
    """Test bottle sensor."""
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

    # Simulate bottle data
    coordinator._realtime_data = {
        "child_1": {
            "feed_status": {
                "prefs": {
                    "lastBottle": {
                        "start": 1234567890,
                        "amount": 120.0,
                        "units": "ml",
                        "bottleType": "Formula"
                    }
                }
            }
        }
    }
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    # Check bottle sensor
    state = hass.states.get("sensor.test_child_last_bottle")
    assert state is not None
    # TIMESTAMP sensor returns datetime object, check it's not None
    assert state.state is not None
    assert state.attributes["amount"] == 120.0
    assert state.attributes["units"] == "ml"
    assert state.attributes["bottle_type"] == "Formula"
    assert state.attributes["amount_display"] == "120.0 ml"
    assert state.attributes["timestamp"] == 1234567890

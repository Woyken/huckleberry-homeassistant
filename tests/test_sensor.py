"""Test Huckleberry sensors."""
from unittest.mock import patch
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from custom_components.huckleberry.const import DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from huckleberry_api.firebase_types import (
    FirebaseDiaperDocumentData,
    FirebaseDiaperPrefs,
    FirebaseFeedDocumentData,
    FirebaseFeedPrefs,
    FirebaseGrowthData,
    FirebaseHealthDocumentData,
    FirebaseHealthPrefs,
    FirebaseLastBottleData,
    FirebaseLastDiaperData,
)


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

    # Simulate growth and diaper data via typed models
    state = coordinator._realtime_data["child_1"]
    state.health_status = FirebaseHealthDocumentData(
        prefs=FirebaseHealthPrefs(
            lastGrowthEntry=FirebaseGrowthData(
                mode="growth",
                start=1234567890,
                lastUpdated=1234567890,
                offset=0,
                weight=10.5,
                weightUnits="kg",
                height=75.0,
                heightUnits="cm",
                head=45.0,
                headUnits="hcm",
            ),
        ),
    )
    state.diaper_status = FirebaseDiaperDocumentData(
        prefs=FirebaseDiaperPrefs(
            lastDiaper=FirebaseLastDiaperData(
                mode="pee",
                start=1234567890,
                offset=0,
            ),
        ),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    # Check children count sensor
    sensor_state = hass.states.get("sensor.huckleberry_children")
    assert sensor_state.state == "1"
    assert sensor_state.attributes["children"][0]["name"] == "Test Child"

    # Check child profile sensor
    sensor_state = hass.states.get("sensor.test_child_profile")
    assert sensor_state.state == "Test Child"
    assert sensor_state.attributes["birthday"] == "2023-01-01"

    # Check growth sensor
    sensor_state = hass.states.get("sensor.test_child_growth")
    from datetime import datetime
    expected_date = datetime.fromtimestamp(1234567890).strftime("%Y-%m-%d %H:%M")
    assert sensor_state.state == expected_date
    assert sensor_state.attributes["weight"] == 10.5
    assert sensor_state.attributes["height"] == 75.0

    # Check diaper sensor
    sensor_state = hass.states.get("sensor.test_child_last_diaper")
    assert sensor_state is not None
    # The sensor returns formatted date, let's just check it's not "No changes logged"
    assert sensor_state.state != "No changes logged"
    assert sensor_state.attributes["mode"] == "pee"
    assert sensor_state.attributes["timestamp"] == 1234567890

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

    # Simulate bottle data via typed models
    state = coordinator._realtime_data["child_1"]
    state.feed_status = FirebaseFeedDocumentData(
        prefs=FirebaseFeedPrefs(
            lastBottle=FirebaseLastBottleData(
                mode="bottle",
                start=1234567890,
                bottleAmount=120.0,
                bottleUnits="ml",
                bottleType="Formula",
                offset=0,
            ),
        ),
    )
    coordinator.async_set_updated_data(dict(coordinator._realtime_data))
    await hass.async_block_till_done()

    # Check bottle sensor
    sensor_state = hass.states.get("sensor.test_child_last_bottle")
    assert sensor_state is not None
    # TIMESTAMP sensor returns datetime object, check it's not None
    assert sensor_state.state is not None
    assert sensor_state.attributes["amount"] == 120.0
    assert sensor_state.attributes["units"] == "ml"
    assert sensor_state.attributes["bottle_type"] == "Formula"
    assert sensor_state.attributes["amount_display"] == "120.0 ml"
    assert sensor_state.attributes["timestamp"] == 1234567890

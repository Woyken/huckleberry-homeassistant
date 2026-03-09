"""Test Huckleberry integration with multiple children.

This test specifically addresses issue #2:
https://github.com/Woyken/huckleberry-homeassistant/issues/2

The issue was that when setting up the integration with an account that has
multiple children, only the entities for one child were loaded correctly,
while all entities belonging to other children were marked as `unavailable`.

The root cause was in the py-huckleberry-api library where it was using
`lastChild` instead of `childList` to fetch children data.
"""
from unittest.mock import patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.huckleberry.const import DOMAIN


async def test_multiple_children_all_entities_created(
    hass: HomeAssistant, mock_huckleberry_api_multiple_children
):
    """Test that all children's entities are created when multiple children exist.

    This is a regression test for issue #2.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "test_password"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api_multiple_children,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state.value == "loaded"
    mock_huckleberry_api_multiple_children.get_children.assert_called()

    # Check children count sensor
    children_sensor = hass.states.get("sensor.huckleberry_children")
    assert children_sensor is not None
    assert children_sensor.state == "3"
    assert len(children_sensor.attributes.get("children", [])) == 3

    # Verify entities exist for all children
    child_names = ["first_child", "second_child", "third_child"]
    for child_name in child_names:
        assert hass.states.get(f"switch.{child_name}_sleep_tracking") is not None
        assert hass.states.get(f"switch.{child_name}_feeding_left") is not None
        assert hass.states.get(f"switch.{child_name}_feeding_right") is not None
        assert hass.states.get(f"sensor.{child_name}_profile") is not None


async def test_multiple_children_devices_created(
    hass: HomeAssistant, mock_huckleberry_api_multiple_children
):
    """Test that separate devices are created for each child."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "test_password"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api_multiple_children,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Verify devices created for each child
    device_reg = dr.async_get(hass)
    devices = [d for d in device_reg.devices.values()
               if any(identifier[0] == DOMAIN for identifier in d.identifiers)]
    assert len(devices) == 3

    # Verify device identifiers match child UIDs
    device_identifiers = {
        identifier[1] for device in devices
        for identifier in device.identifiers if identifier[0] == DOMAIN
    }
    assert device_identifiers == {"child_1", "child_2", "child_3"}


async def test_single_child_still_works(hass: HomeAssistant, mock_huckleberry_api):
    """Test that the integration still works correctly with a single child."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "test_password"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state.value == "loaded"

    # Check children count sensor
    children_sensor = hass.states.get("sensor.huckleberry_children")
    assert children_sensor is not None
    assert children_sensor.state == "1"

    # Verify child's entities exist
    assert hass.states.get("switch.test_child_sleep_tracking") is not None
    assert hass.states.get("sensor.test_child_profile") is not None


async def test_multiple_children_sensors_update_independently(
    hass: HomeAssistant, mock_huckleberry_api_multiple_children
):
    """Test that sensor updates for one child don't affect other children."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "test_password"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api_multiple_children,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Get the coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Simulate sleep active for first child only
    coordinator._realtime_data = {
        "child_1": {
            "child": {"uid": "child_1", "name": "First Child"},
            "sleep_status": {
                "timer": {"active": True, "paused": False},
            },
            "feed_status": {},
            "growth_data": {},
        },
        "child_2": {
            "child": {"uid": "child_2", "name": "Second Child"},
            "sleep_status": {},
            "feed_status": {
                "timer": {"active": True, "paused": False, "activeSide": "right"},
            },
            "growth_data": {},
        },
        "child_3": {
            "child": {"uid": "child_3", "name": "Third Child"},
            "sleep_status": {},
            "feed_status": {},
            "growth_data": {},
        },
    }
    # Update coordinator.data to point to _realtime_data
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    # Verify first child's sleep is on, others are off
    first_sleep = hass.states.get("switch.first_child_sleep_tracking")
    assert first_sleep is not None
    assert first_sleep.state == STATE_ON
    second_sleep = hass.states.get("switch.second_child_sleep_tracking")
    assert second_sleep is not None
    assert second_sleep.state == STATE_OFF
    third_sleep = hass.states.get("switch.third_child_sleep_tracking")
    assert third_sleep is not None
    assert third_sleep.state == STATE_OFF

    # Verify second child's feeding is on, others are off
    first_feeding = hass.states.get("switch.first_child_feeding_right")
    assert first_feeding is not None
    assert first_feeding.state == STATE_OFF
    second_feeding = hass.states.get("switch.second_child_feeding_right")
    assert second_feeding is not None
    assert second_feeding.state == STATE_ON
    third_feeding = hass.states.get("switch.third_child_feeding_right")
    assert third_feeding is not None
    assert third_feeding.state == STATE_OFF

    # Verify sleep status sensors
    first_sleep_status = hass.states.get("sensor.first_child_sleep_status")
    assert first_sleep_status is not None
    assert first_sleep_status.state == "sleeping"
    second_sleep_status = hass.states.get("sensor.second_child_sleep_status")
    assert second_sleep_status is not None
    assert second_sleep_status.state == "none"
    third_sleep_status = hass.states.get("sensor.third_child_sleep_status")
    assert third_sleep_status is not None
    assert third_sleep_status.state == "none"

    # Verify feeding status sensors
    first_feeding_status = hass.states.get("sensor.first_child_feeding_status")
    assert first_feeding_status is not None
    assert first_feeding_status.state == "none"
    second_feeding_status = hass.states.get("sensor.second_child_feeding_status")
    assert second_feeding_status is not None
    assert second_feeding_status.state == "feeding"
    third_feeding_status = hass.states.get("sensor.third_child_feeding_status")
    assert third_feeding_status is not None
    assert third_feeding_status.state == "none"

    # Now update third child with paused sleep
    coordinator._realtime_data["child_3"]["sleep_status"] = {
        "timer": {"active": True, "paused": True},
    }
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    # Verify third child's sleep status is paused (switch shows off when paused)
    third_sleep_updated = hass.states.get("switch.third_child_sleep_tracking")
    assert third_sleep_updated is not None
    assert third_sleep_updated.state == STATE_OFF  # Switch is off when paused
    third_sleep_status_updated = hass.states.get("sensor.third_child_sleep_status")
    assert third_sleep_status_updated is not None
    assert third_sleep_status_updated.state == "paused"

    # Verify other children's states haven't changed
    first_sleep_still = hass.states.get("switch.first_child_sleep_tracking")
    assert first_sleep_still is not None
    assert first_sleep_still.state == STATE_ON
    second_feeding_still = hass.states.get("switch.second_child_feeding_right")
    assert second_feeding_still is not None
    assert second_feeding_still.state == STATE_ON

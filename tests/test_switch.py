"""Test Huckleberry switches."""
from unittest.mock import patch, MagicMock
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, STATE_ON, STATE_OFF
from custom_components.huckleberry.const import DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_switches(hass: HomeAssistant, mock_huckleberry_api):
    """Test switches."""
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

    # Simulate sleep active
    coordinator._realtime_data = {
        "child_1": {
            "sleep_status": {
                "timer": {"active": True, "paused": False},
            },
            "feed_status": {
                "timer": {"active": True, "paused": False, "activeSide": "left"},
            }
        }
    }
    coordinator.async_set_updated_data(coordinator._realtime_data)
    await hass.async_block_till_done()

    # Check sleep switch
    state = hass.states.get("switch.test_child_sleep_tracking")
    assert state.state == STATE_ON

    # Check feeding switches
    state_left = hass.states.get("switch.test_child_feeding_left")
    state_right = hass.states.get("switch.test_child_feeding_right")
    assert state_left.state == STATE_ON
    assert state_right.state == STATE_OFF

    # Test turning off sleep
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.test_child_sleep_tracking"}, blocking=True
    )
    mock_huckleberry_api.complete_sleep.assert_called_with("child_1")

    # Test turning on sleep
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.test_child_sleep_tracking"}, blocking=True
    )
    mock_huckleberry_api.start_sleep.assert_called_with("child_1")

    # Test turning on right feeding (should switch side)
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.test_child_feeding_right"}, blocking=True
    )
    mock_huckleberry_api.start_feeding.assert_called_with("child_1", "right")

"""Test Huckleberry device actions."""
from unittest.mock import patch
import pytest
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.huckleberry.const import DOMAIN
from custom_components.huckleberry import device_action

async def test_get_actions(hass: HomeAssistant):
    """Test we get all expected actions."""
    device_id = "test_device_id"
    actions = await device_action.async_get_actions(hass, device_id)

    expected_actions = {
        "start_sleep", "pause_sleep", "resume_sleep", "cancel_sleep", "complete_sleep",
        "start_feeding_left", "start_feeding_right", "pause_feeding", "resume_feeding",
        "switch_feeding_side", "cancel_feeding", "complete_feeding",
        "log_diaper_pee", "log_diaper_poo", "log_diaper_both", "log_diaper_dry",
        "log_growth", "log_bottle"
    }

    found_actions = {action[CONF_TYPE] for action in actions}
    assert found_actions == expected_actions

    for action in actions:
        assert action[CONF_DEVICE_ID] == device_id
        assert action[CONF_DOMAIN] == DOMAIN

async def test_call_action(hass: HomeAssistant):
    """Test executing actions calls the correct service."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "test_child_uid")},
        name="Test Child"
    )

    # Test mapping of action types to service calls
    test_cases = [
        ("start_sleep", "start_sleep", {"child_uid": "test_child_uid"}),
        ("pause_sleep", "pause_sleep", {"child_uid": "test_child_uid"}),
        ("resume_sleep", "resume_sleep", {"child_uid": "test_child_uid"}),
        ("cancel_sleep", "cancel_sleep", {"child_uid": "test_child_uid"}),
        ("complete_sleep", "complete_sleep", {"child_uid": "test_child_uid"}),
        ("start_feeding_left", "start_feeding", {"child_uid": "test_child_uid", "side": "left"}),
        ("start_feeding_right", "start_feeding", {"child_uid": "test_child_uid", "side": "right"}),
        ("pause_feeding", "pause_feeding", {"child_uid": "test_child_uid"}),
        ("resume_feeding", "resume_feeding", {"child_uid": "test_child_uid"}),
        ("switch_feeding_side", "switch_feeding_side", {"child_uid": "test_child_uid"}),
        ("cancel_feeding", "cancel_feeding", {"child_uid": "test_child_uid"}),
        ("complete_feeding", "complete_feeding", {"child_uid": "test_child_uid"}),
        ("log_diaper_pee", "log_diaper_pee", {"child_uid": "test_child_uid"}),
        ("log_diaper_poo", "log_diaper_poo", {"child_uid": "test_child_uid"}),
        ("log_diaper_both", "log_diaper_both", {"child_uid": "test_child_uid"}),
        ("log_diaper_dry", "log_diaper_dry", {"child_uid": "test_child_uid"}),
        ("log_growth", "log_growth", {"child_uid": "test_child_uid"}),
        ("log_bottle", "log_bottle", {"child_uid": "test_child_uid"}),
    ]

    for action_type, service, service_data in test_cases:
        with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
            await device_action.async_call_action_from_config(
                hass,
                {CONF_DEVICE_ID: device.id, CONF_TYPE: action_type},
                {},
                None
            )

            mock_service_call.assert_called_once_with(
                DOMAIN,
                service,
                service_data,
                blocking=True,
                context=None
            )

async def test_call_action_no_device(hass: HomeAssistant):
    """Test action with invalid device ID."""
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        await device_action.async_call_action_from_config(
            hass,
            {CONF_DEVICE_ID: "invalid_device", CONF_TYPE: "start_sleep"},
            {},
            None
        )
        mock_service_call.assert_not_called()

async def test_call_action_no_child_uid(hass: HomeAssistant):
    """Test action with device missing child_uid."""
    entry = MockConfigEntry(domain="other_domain", data={})
    entry.add_to_hass(hass)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("other_domain", "some_id")},
        name="Other Device"
    )

    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
        await device_action.async_call_action_from_config(
            hass,
            {CONF_DEVICE_ID: device.id, CONF_TYPE: "start_sleep"},
            {},
            None
        )
        mock_service_call.assert_not_called()

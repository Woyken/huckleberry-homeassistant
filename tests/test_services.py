"""Test Huckleberry services."""
from unittest.mock import patch, MagicMock
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from custom_components.huckleberry.const import DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_services(hass: HomeAssistant, mock_huckleberry_api):
    """Test all services."""
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

    # Create a device to target
    device_registry = hass.helpers.device_registry.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "test_child_uid")},
        name="Test Child"
    )

    # Test start_sleep
    await hass.services.async_call(
        DOMAIN, "start_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.start_sleep.assert_called_with("test_child_uid")

    # Test pause_sleep
    await hass.services.async_call(
        DOMAIN, "pause_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.pause_sleep.assert_called_with("test_child_uid")

    # Test resume_sleep
    await hass.services.async_call(
        DOMAIN, "resume_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.resume_sleep.assert_called_with("test_child_uid")

    # Test cancel_sleep
    await hass.services.async_call(
        DOMAIN, "cancel_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.cancel_sleep.assert_called_with("test_child_uid")

    # Test complete_sleep
    await hass.services.async_call(
        DOMAIN, "complete_sleep", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.complete_sleep.assert_called_with("test_child_uid")

    # Test start_feeding (left)
    await hass.services.async_call(
        DOMAIN, "start_feeding", {"device_id": device.id, "side": "left"}, blocking=True
    )
    mock_huckleberry_api.start_feeding.assert_called_with("test_child_uid", "left")

    # Test start_feeding (right)
    await hass.services.async_call(
        DOMAIN, "start_feeding", {"device_id": device.id, "side": "right"}, blocking=True
    )
    mock_huckleberry_api.start_feeding.assert_called_with("test_child_uid", "right")

    # Test pause_feeding
    await hass.services.async_call(
        DOMAIN, "pause_feeding", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.pause_feeding.assert_called_with("test_child_uid")

    # Test resume_feeding
    await hass.services.async_call(
        DOMAIN, "resume_feeding", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.resume_feeding.assert_called_with("test_child_uid", None)

    # Test switch_feeding_side
    await hass.services.async_call(
        DOMAIN, "switch_feeding_side", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.switch_feeding_side.assert_called_with("test_child_uid")

    # Test cancel_feeding
    await hass.services.async_call(
        DOMAIN, "cancel_feeding", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.cancel_feeding.assert_called_with("test_child_uid")

    # Test complete_feeding
    await hass.services.async_call(
        DOMAIN, "complete_feeding", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.complete_feeding.assert_called_with("test_child_uid")

    # Test log_diaper_pee
    await hass.services.async_call(
        DOMAIN, "log_diaper_pee", {"device_id": device.id, "pee_amount": "medium"}, blocking=True
    )
    mock_huckleberry_api.log_diaper.assert_called_with(
        "test_child_uid", "pee", "medium", None, None, None, False, None
    )

    # Test log_diaper_poo
    await hass.services.async_call(
        DOMAIN, "log_diaper_poo", {"device_id": device.id, "poo_amount": "big", "color": "brown", "consistency": "solid"}, blocking=True
    )
    mock_huckleberry_api.log_diaper.assert_called_with(
        "test_child_uid", "poo", None, "big", "brown", "solid", False, None
    )

    # Test log_diaper_both
    await hass.services.async_call(
        DOMAIN, "log_diaper_both", {"device_id": device.id, "pee_amount": "little", "poo_amount": "medium"}, blocking=True
    )
    mock_huckleberry_api.log_diaper.assert_called_with(
        "test_child_uid", "both", "little", "medium", None, None, False, None
    )

    # Test log_diaper_dry
    await hass.services.async_call(
        DOMAIN, "log_diaper_dry", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api.log_diaper.assert_called_with(
        "test_child_uid", "dry", None, None, None, None, False, None
    )

    # Test log_growth
    await hass.services.async_call(
        DOMAIN, "log_growth", {"device_id": device.id, "weight": 10.5, "height": 75.0, "head": 45.0, "units": "metric"}, blocking=True
    )
    mock_huckleberry_api.log_growth.assert_called_with(
        "test_child_uid", 10.5, 75.0, 45.0, "metric"
    )

    # Test log_bottle
    await hass.services.async_call(
        DOMAIN, "log_bottle", {"device_id": device.id, "amount": 4.0, "bottle_type": "Formula", "units": "oz"}, blocking=True
    )
    mock_huckleberry_api.log_bottle_feeding.assert_called_with(
        "test_child_uid", 4.0, "Formula", "oz"
    )

async def test_service_explicit_child_uid(hass: HomeAssistant, mock_huckleberry_api):
    """Test service call with explicit child_uid."""
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

    # Create a dummy device ID (not linked to child)
    device_id = "dummy_device_id"

    # Call service with explicit child_uid
    await hass.services.async_call(
        DOMAIN, "start_sleep", {"device_id": device_id, "child_uid": "explicit_child_uid"}, blocking=True
    )
    mock_huckleberry_api.start_sleep.assert_called_with("explicit_child_uid")

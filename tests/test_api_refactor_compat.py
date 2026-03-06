"""Compatibility tests for refactored py-huckleberry-api interface."""

from unittest.mock import patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.huckleberry.const import DOMAIN


async def test_setup_with_refactored_api_surface(
    hass: HomeAssistant, mock_huckleberry_api_refactored
):
    """Ensure setup supports get_user/get_child based child discovery."""
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
        return_value=mock_huckleberry_api_refactored,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    data = hass.data[DOMAIN][entry.entry_id]
    assert len(data["children"]) == 1
    assert data["children"][0]["uid"] == "child_1"
    mock_huckleberry_api_refactored.get_user.assert_awaited()
    mock_huckleberry_api_refactored.get_child.assert_awaited_with("child_1")


async def test_services_use_refactored_nursing_and_bottle_methods(
    hass: HomeAssistant, mock_huckleberry_api_refactored
):
    """Ensure services map to refactored nursing/bottle API method names."""
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
        return_value=mock_huckleberry_api_refactored,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    device_registry = hass.helpers.device_registry.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "child_1")},
        name="Test Child",
    )

    await hass.services.async_call(
        DOMAIN, "start_feeding", {"device_id": device.id, "side": "left"}, blocking=True
    )
    mock_huckleberry_api_refactored.start_nursing.assert_awaited_with("child_1", "left")

    await hass.services.async_call(
        DOMAIN, "complete_feeding", {"device_id": device.id}, blocking=True
    )
    mock_huckleberry_api_refactored.complete_nursing.assert_awaited_with("child_1")

    await hass.services.async_call(
        DOMAIN,
        "log_bottle",
        {"device_id": device.id, "amount": 120.0, "bottle_type": "Formula", "units": "ml"},
        blocking=True,
    )
    mock_huckleberry_api_refactored.log_bottle.assert_awaited_with(
        "child_1", 120.0, "Formula", "ml"
    )

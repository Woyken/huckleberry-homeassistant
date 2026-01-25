"""Test Huckleberry config flow."""
from unittest.mock import patch
import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from custom_components.huckleberry.const import DOMAIN

async def test_flow_user_init(hass: HomeAssistant):
    """Test the initialization of the form in the user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

async def test_flow_user_success(hass: HomeAssistant, mock_huckleberry_api):
    """Test successful flow."""
    mock_huckleberry_api.user_uid = "test_user_uid"
    with patch(
        "custom_components.huckleberry.config_flow.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ), patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Huckleberry (test@example.com)"
    assert result["data"] == {
        CONF_EMAIL: "test@example.com",
        CONF_PASSWORD: "test_password",
    }
    assert result["result"].unique_id == "test_user_uid"

async def test_flow_user_invalid_auth(hass: HomeAssistant, mock_huckleberry_api):
    """Test flow with invalid authentication."""
    import requests

    mock_huckleberry_api.authenticate.side_effect = requests.exceptions.HTTPError(
        response=type("Response", (), {"status_code": 400})()
    )

    with patch(
        "custom_components.huckleberry.config_flow.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ), patch("custom_components.huckleberry.config_flow._LOGGER"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "wrong_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

async def test_flow_user_cannot_connect(hass: HomeAssistant, mock_huckleberry_api):
    """Test flow with connection error."""
    import requests.exceptions
    mock_huckleberry_api.authenticate.side_effect = requests.exceptions.ConnectionError("Connection refused")

    with patch(
        "custom_components.huckleberry.config_flow.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ), patch("custom_components.huckleberry.config_flow._LOGGER"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_user_unknown_error(hass: HomeAssistant, mock_huckleberry_api):
    """Test flow with unknown error."""
    mock_huckleberry_api.authenticate.side_effect = Exception("Something unexpected")

    with patch(
        "custom_components.huckleberry.config_flow.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ), patch("custom_components.huckleberry.config_flow._LOGGER"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}

async def test_flow_user_no_children(hass: HomeAssistant, mock_huckleberry_api):
    """Test flow with no children found."""
    mock_huckleberry_api.get_children.return_value = []

    with patch(
        "custom_components.huckleberry.config_flow.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "test_password",
            },
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "no_children"}

"""Config flow for Huckleberry integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from huckleberry_api import HuckleberryAPI

from . import _async_load_children
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Huckleberry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if user_input is not None:
            try:
                api = HuckleberryAPI(
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    timezone=str(self.hass.config.time_zone),
                    websession=async_get_clientsession(self.hass),
                )

                await api.authenticate()
                children = await _async_load_children(api)

                if not children:
                    errors["base"] = "no_children"
                else:
                    await self.async_set_unique_id(api.user_uid)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Huckleberry ({user_input[CONF_EMAIL]})",
                        data=user_input,
                    )

            except aiohttp.ClientResponseError as err:
                _LOGGER.exception("HTTP error during authentication")
                if err.status == 400:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
                description_placeholders["error_details"] = f"\n\n**Error:** {err.status} {err.message}"
            except aiohttp.ServerTimeoutError as err:
                _LOGGER.exception("Timeout during authentication")
                errors["base"] = "timeout"
                description_placeholders["error_details"] = f"\n\n**Error:** {err}"
            except aiohttp.ClientConnectionError as err:
                _LOGGER.exception("Connection error during authentication")
                errors["base"] = "cannot_connect"
                description_placeholders["error_details"] = f"\n\n**Error:** {err}"
            except Exception as err:
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"
                description_placeholders["error_details"] = f"\n\n**Error:** {type(err).__name__}: {err}"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"error_details": description_placeholders.get("error_details", "")},
        )

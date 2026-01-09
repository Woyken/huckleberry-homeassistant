"""Config flow for Huckleberry integration."""
from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.util import dt as dt_util

from huckleberry_api import HuckleberryAPI
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
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Test authentication
                api = HuckleberryAPI(
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    timezone='UTC',
                )

                await self.hass.async_add_executor_job(api.authenticate)

                # Get children to verify account has data
                children = await self.hass.async_add_executor_job(api.get_children)

                if not children:
                    errors["base"] = "no_children"
                else:
                    # Create entry
                    await self.async_set_unique_id(api.user_uid)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Huckleberry ({user_input[CONF_EMAIL]})",
                        data=user_input,
                    )

            except requests.exceptions.HTTPError as err:
                _LOGGER.exception("HTTP error during authentication")
                if err.response is not None and err.response.status_code == 400:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

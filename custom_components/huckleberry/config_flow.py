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
        description_placeholders: dict[str, str] = {}

        if user_input is not None:
            try:
                # Test authentication
                api = HuckleberryAPI(
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                    timezone=str(self.hass.config.time_zone),
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
                error_code = "cannot_connect"
                error_detail = str(err)
                if err.response is not None:
                    # Try to parse Firebase error message
                    try:
                        error_data = err.response.json()
                        firebase_error = error_data.get("error", {}).get("message", "")
                        _LOGGER.error("Firebase error: %s", firebase_error)
                        if firebase_error:
                            error_detail = f"{firebase_error} ({err})"

                        # Map Firebase errors to user-friendly messages
                        # Use startswith() to handle errors with extra info like "INVALID_PASSWORD : ..."
                        if any(firebase_error.startswith(e) for e in ("INVALID_PASSWORD", "EMAIL_NOT_FOUND", "INVALID_EMAIL")):
                            error_code = "invalid_auth"
                        elif firebase_error.startswith("USER_DISABLED"):
                            error_code = "account_disabled"
                        elif firebase_error.startswith("TOO_MANY_ATTEMPTS_TRY_LATER"):
                            error_code = "too_many_attempts"
                        elif err.response.status_code == 400:
                            error_code = "invalid_auth"
                    except Exception:  # pylint: disable=broad-except
                        # JSON parsing failed, try to include response body for debugging
                        try:
                            response_text = err.response.text[:200]
                            error_detail = f"{err} - Response: {response_text}"
                        except Exception:  # pylint: disable=broad-except
                            pass  # Keep original error_detail = str(err)
                        if err.response.status_code == 400:
                            error_code = "invalid_auth"
                errors["base"] = error_code
                description_placeholders["error_details"] = f"\n\n**Error:** {error_detail}"
            except requests.exceptions.ConnectionError as err:
                _LOGGER.exception("Connection error during authentication")
                errors["base"] = "cannot_connect"
                description_placeholders["error_details"] = f"\n\n**Error:** {err}"
            except requests.exceptions.Timeout as err:
                _LOGGER.exception("Timeout during authentication")
                errors["base"] = "timeout"
                description_placeholders["error_details"] = f"\n\n**Error:** {err}"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", type(err).__name__)
                errors["base"] = "unknown"
                description_placeholders["error_details"] = f"\n\n**Error:** {type(err).__name__}: {err}"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"error_details": description_placeholders.get("error_details", "")},
        )

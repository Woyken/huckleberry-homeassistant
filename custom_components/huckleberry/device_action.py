"""Provides device actions for Huckleberry."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_TYPE
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import DOMAIN

ACTION_TYPES = {
    "start_sleep",
    "pause_sleep",
    "resume_sleep",
    "cancel_sleep",
    "complete_sleep",
    "start_nursing_left",
    "start_nursing_right",
    "pause_nursing",
    "resume_nursing",
    "switch_nursing_side",
    "cancel_nursing",
    "complete_nursing",
    "log_diaper_pee",
    "log_diaper_poo",
    "log_diaper_both",
    "log_diaper_dry",
    "log_growth",
    "log_bottle",
}

# Map device action type → (service_name, extra_service_data)
_ACTION_TO_SERVICE: dict[str, tuple[str, dict[str, str]]] = {
    "start_sleep": ("start_sleep", {}),
    "pause_sleep": ("pause_sleep", {}),
    "resume_sleep": ("resume_sleep", {}),
    "cancel_sleep": ("cancel_sleep", {}),
    "complete_sleep": ("complete_sleep", {}),
    "start_nursing_left": ("start_nursing", {"side": "left"}),
    "start_nursing_right": ("start_nursing", {"side": "right"}),
    "pause_nursing": ("pause_nursing", {}),
    "resume_nursing": ("resume_nursing", {}),
    "switch_nursing_side": ("switch_nursing_side", {}),
    "cancel_nursing": ("cancel_nursing", {}),
    "complete_nursing": ("complete_nursing", {}),
    "log_diaper_pee": ("log_diaper_pee", {}),
    "log_diaper_poo": ("log_diaper_poo", {}),
    "log_diaper_both": ("log_diaper_both", {}),
    "log_diaper_dry": ("log_diaper_dry", {}),
    "log_growth": ("log_growth", {}),
    "log_bottle": ("log_bottle", {}),
}

ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ACTION_TYPES),
    }
)


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device actions for Huckleberry devices."""
    return [
        {CONF_DEVICE_ID: device_id, CONF_DOMAIN: DOMAIN, CONF_TYPE: action_type}
        for action_type in ACTION_TYPES
    ]


async def async_call_action_from_config(
    hass: HomeAssistant, config: dict, variables: dict, context: Context | None
) -> None:
    """Execute a device action."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(config[CONF_DEVICE_ID])

    if not device:
        return

    child_uid = next(
        (
            identifier_value
            for identifier_domain, identifier_value in device.identifiers
            if identifier_domain == DOMAIN
        ),
        None,
    )

    if not child_uid:
        return

    action_type = config[CONF_TYPE]
    mapping = _ACTION_TO_SERVICE.get(action_type)
    if mapping is None:
        return

    service_name, extra_data = mapping
    await hass.services.async_call(
        DOMAIN,
        service_name,
        {"child_uid": child_uid, **extra_data},
        blocking=True,
        context=context,
    )

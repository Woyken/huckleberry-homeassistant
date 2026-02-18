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
    "start_feeding_left",
    "start_feeding_right",
    "pause_feeding",
    "resume_feeding",
    "switch_feeding_side",
    "cancel_feeding",
    "complete_feeding",
    "log_diaper_pee",
    "log_diaper_poo",
    "log_diaper_both",
    "log_diaper_dry",
    "log_growth",
    "log_bottle",
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
    actions = []

    # Add sleep actions
    for action_type in [
        "start_sleep",
        "pause_sleep",
        "resume_sleep",
        "cancel_sleep",
        "complete_sleep",
    ]:
        actions.append(
            {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: action_type,
            }
        )

    # Add feeding actions
    for action_type in [
        "start_feeding_left",
        "start_feeding_right",
        "pause_feeding",
        "resume_feeding",
        "switch_feeding_side",
        "cancel_feeding",
        "complete_feeding",
    ]:
        actions.append(
            {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: action_type,
            }
        )

    # Add diaper actions
    for action_type in [
        "log_diaper_pee",
        "log_diaper_poo",
        "log_diaper_both",
        "log_diaper_dry",
    ]:
        actions.append(
            {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: action_type,
            }
        )

    # Add growth action
    actions.append(
        {
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: "log_growth",
        }
    )

    # Add bottle action
    actions.append(
        {
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: "log_bottle",
        }
    )

    return actions


async def async_call_action_from_config(
    hass: HomeAssistant, config: dict, variables: dict, context: Context | None
) -> None:
    """Execute a device action."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(config[CONF_DEVICE_ID])

    if not device:
        return

    # Find child_uid from device identifiers
    child_uid = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            child_uid = identifier[1]
            break

    if not child_uid:
        return

    action_type = config[CONF_TYPE]

    # Map device actions to service calls
    if action_type == "start_sleep":
        await hass.services.async_call(
            DOMAIN,
            "start_sleep",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "pause_sleep":
        await hass.services.async_call(
            DOMAIN,
            "pause_sleep",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "resume_sleep":
        await hass.services.async_call(
            DOMAIN,
            "resume_sleep",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "cancel_sleep":
        await hass.services.async_call(
            DOMAIN,
            "cancel_sleep",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "complete_sleep":
        await hass.services.async_call(
            DOMAIN,
            "complete_sleep",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "start_feeding_left":
        await hass.services.async_call(
            DOMAIN,
            "start_feeding",
            {"child_uid": child_uid, "side": "left"},
            blocking=True,
            context=context,
        )
    elif action_type == "start_feeding_right":
        await hass.services.async_call(
            DOMAIN,
            "start_feeding",
            {"child_uid": child_uid, "side": "right"},
            blocking=True,
            context=context,
        )
    elif action_type == "pause_feeding":
        await hass.services.async_call(
            DOMAIN,
            "pause_feeding",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "resume_feeding":
        await hass.services.async_call(
            DOMAIN,
            "resume_feeding",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "switch_feeding_side":
        await hass.services.async_call(
            DOMAIN,
            "switch_feeding_side",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "cancel_feeding":
        await hass.services.async_call(
            DOMAIN,
            "cancel_feeding",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "complete_feeding":
        await hass.services.async_call(
            DOMAIN,
            "complete_feeding",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "log_diaper_pee":
        await hass.services.async_call(
            DOMAIN,
            "log_diaper_pee",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "log_diaper_poo":
        await hass.services.async_call(
            DOMAIN,
            "log_diaper_poo",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "log_diaper_both":
        await hass.services.async_call(
            DOMAIN,
            "log_diaper_both",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "log_diaper_dry":
        await hass.services.async_call(
            DOMAIN,
            "log_diaper_dry",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "log_growth":
        await hass.services.async_call(
            DOMAIN,
            "log_growth",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )
    elif action_type == "log_bottle":
        await hass.services.async_call(
            DOMAIN,
            "log_bottle",
            {"child_uid": child_uid},
            blocking=True,
            context=context,
        )

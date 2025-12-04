"""Huckleberry Baby Sleep Tracker integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import TypedDict, NotRequired

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from huckleberry_api import (
    HuckleberryAPI,
    ChildData,
    SleepDocumentData,
    FeedDocumentData,
    GrowthData,
    DiaperDocumentData,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SWITCH, Platform.SENSOR]


# Type definitions for integration data structures
class HuckleberryEntryData(TypedDict):
    """Data stored in hass.data[DOMAIN][entry.entry_id]."""
    api: HuckleberryAPI
    coordinator: "HuckleberryDataUpdateCoordinator"
    children: list[ChildData]


class ChildRealtimeData(TypedDict):
    """Real-time data structure for a single child."""
    child: ChildData
    sleep_status: NotRequired[SleepDocumentData]
    feed_status: NotRequired[FeedDocumentData]
    growth_data: NotRequired[GrowthData]
    diaper_data: NotRequired[DiaperDocumentData]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Huckleberry from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = HuckleberryAPI(
        email=entry.data["email"],
        password=entry.data["password"],
    )

    # Authenticate
    try:
        await hass.async_add_executor_job(api.authenticate)
    except Exception as err:
        _LOGGER.error("Failed to authenticate with Huckleberry: %s", err)
        return False

    # Get children
    try:
        children = await hass.async_add_executor_job(api.get_children)
        if not children:
            _LOGGER.error("No children found in Huckleberry account")
            return False
    except Exception as err:
        _LOGGER.error("Failed to get children from Huckleberry: %s", err)
        return False

    # Create coordinator for data updates
    coordinator = HuckleberryDataUpdateCoordinator(hass, api, children)
    await coordinator.async_config_entry_first_refresh()

    # Set up real-time listeners for instant updates
    await coordinator.async_setup_listeners()

    entry_data: HuckleberryEntryData = {
        "api": api,
        "coordinator": coordinator,
        "children": children,
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Helper to get child_uid from service call (device target or explicit child_uid)
    def _get_child_uid_from_call(call: ServiceCall) -> str | None:
        """Extract child_uid from service call, either from device target or data field."""
        # First check if child_uid explicitly provided
        if child_uid := call.data.get("child_uid"):
            return child_uid

        # Check if device target provided
        if "device_id" in call.data:
            device_registry = dr.async_get(hass)
            device = device_registry.async_get(call.data["device_id"])
            if device:
                for identifier in device.identifiers:
                    if identifier[0] == DOMAIN:
                        return identifier[1]

        # Fallback to first child
        return children[0]["uid"] if children else None

    # Register services for advanced control
    async def _call_api(method_name: str, call: ServiceCall) -> None:
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        target_child = _get_child_uid_from_call(call)
        if not target_child:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        _LOGGER.info("Calling %s for child %s", method_name, target_child)
        method = getattr(api, method_name)
        await hass.async_add_executor_job(method, target_child)
        _LOGGER.info("Completed %s for child %s", method_name, target_child)

    async def handle_start_sleep(call):
        await _call_api("start_sleep", call)

    async def handle_pause_sleep(call):
        await _call_api("pause_sleep", call)

    async def handle_resume_sleep(call):
        await _call_api("resume_sleep", call)

    async def handle_cancel_sleep(call):
        await _call_api("cancel_sleep", call)

    async def handle_complete_sleep(call):
        await _call_api("complete_sleep", call)

    # Feeding service handlers
    async def handle_start_feeding(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        side = call.data.get("side", "left")
        _LOGGER.info("Starting feeding for child %s on %s side", child_uid, side)
        await hass.async_add_executor_job(api.start_feeding, child_uid, side)

    async def handle_pause_feeding(call):
        await _call_api("pause_feeding", call)

    async def handle_resume_feeding(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        side = call.data.get("side")  # Optional side parameter
        _LOGGER.info("Resuming feeding for child %s on %s", child_uid, side if side else "current side")
        await hass.async_add_executor_job(api.resume_feeding, child_uid, side)

    async def handle_switch_feeding_side(call):
        await _call_api("switch_feeding_side", call)

    async def handle_cancel_feeding(call):
        await _call_api("cancel_feeding", call)

    async def handle_complete_feeding(call):
        await _call_api("complete_feeding", call)

    # Diaper service handlers
    async def handle_log_diaper_pee(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        pee_amount = call.data.get("pee_amount")
        diaper_rash = call.data.get("diaper_rash", False)
        notes = call.data.get("notes")
        _LOGGER.info("Logging pee diaper for child %s (amount=%s)", child_uid, pee_amount)
        await hass.async_add_executor_job(
            api.log_diaper, child_uid, "pee", pee_amount, None, None, None, diaper_rash, notes
        )

    async def handle_log_diaper_poo(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        poo_amount = call.data.get("poo_amount")
        color = call.data.get("color")
        consistency = call.data.get("consistency")
        diaper_rash = call.data.get("diaper_rash", False)
        notes = call.data.get("notes")
        _LOGGER.info("Logging poo diaper for child %s (amount=%s, color=%s, consistency=%s)",
                     child_uid, poo_amount, color, consistency)
        await hass.async_add_executor_job(
            api.log_diaper, child_uid, "poo", None, poo_amount, color, consistency, diaper_rash, notes
        )

    async def handle_log_diaper_both(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        pee_amount = call.data.get("pee_amount")
        poo_amount = call.data.get("poo_amount")
        color = call.data.get("color")
        consistency = call.data.get("consistency")
        diaper_rash = call.data.get("diaper_rash", False)
        notes = call.data.get("notes")
        _LOGGER.info("Logging both (pee+poo) diaper for child %s", child_uid)
        await hass.async_add_executor_job(
            api.log_diaper, child_uid, "both", pee_amount, poo_amount, color, consistency, diaper_rash, notes
        )

    async def handle_log_diaper_dry(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        diaper_rash = call.data.get("diaper_rash", False)
        notes = call.data.get("notes")
        _LOGGER.info("Logging dry diaper check for child %s", child_uid)
        await hass.async_add_executor_job(
            api.log_diaper, child_uid, "dry", None, None, None, None, diaper_rash, notes
        )

    async def handle_log_growth(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        weight = call.data.get("weight")
        height = call.data.get("height")
        head = call.data.get("head")
        units = call.data.get("units", "metric")
        _LOGGER.info("Logging growth for child %s (weight=%s, height=%s, head=%s, units=%s)",
                     child_uid, weight, height, head, units)
        await hass.async_add_executor_job(
            api.log_growth, child_uid, weight, height, head, units
        )
        # Refresh coordinator to update growth sensor
        coordinator: HuckleberryDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_request_refresh()

    service_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
    })

    feeding_start_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
        vol.Optional("side"): vol.In(["left", "right"]),
    })

    feeding_resume_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
        vol.Optional("side"): vol.In(["left", "right"]),
    })

    feeding_service_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
    })

    diaper_pee_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
        vol.Optional("pee_amount"): vol.In(["little", "medium", "big"]),
        vol.Optional("diaper_rash"): cv.boolean,
        vol.Optional("notes"): cv.string,
    })

    diaper_poo_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
        vol.Optional("poo_amount"): vol.In(["little", "medium", "big"]),
        vol.Optional("color"): vol.In(["yellow", "brown", "black", "green", "red", "gray"]),
        vol.Optional("consistency"): vol.In(["solid", "loose", "runny", "mucousy", "hard", "pebbles", "diarrhea"]),
        vol.Optional("diaper_rash"): cv.boolean,
        vol.Optional("notes"): cv.string,
    })

    diaper_both_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
        vol.Optional("pee_amount"): vol.In(["little", "medium", "big"]),
        vol.Optional("poo_amount"): vol.In(["little", "medium", "big"]),
        vol.Optional("color"): vol.In(["yellow", "brown", "black", "green", "red", "gray"]),
        vol.Optional("consistency"): vol.In(["solid", "loose", "runny", "mucousy", "hard", "pebbles", "diarrhea"]),
        vol.Optional("diaper_rash"): cv.boolean,
        vol.Optional("notes"): cv.string,
    })

    diaper_dry_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
        vol.Optional("diaper_rash"): cv.boolean,
        vol.Optional("notes"): cv.string,
    })

    growth_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
        vol.Optional("weight"): vol.Coerce(float),
        vol.Optional("height"): vol.Coerce(float),
        vol.Optional("head"): vol.Coerce(float),
        vol.Optional("units"): vol.In(["metric", "imperial"]),
    })

    hass.services.async_register(DOMAIN, "start_sleep", handle_start_sleep, schema=service_schema)
    hass.services.async_register(DOMAIN, "pause_sleep", handle_pause_sleep, schema=service_schema)
    hass.services.async_register(DOMAIN, "resume_sleep", handle_resume_sleep, schema=service_schema)
    hass.services.async_register(DOMAIN, "cancel_sleep", handle_cancel_sleep, schema=service_schema)
    hass.services.async_register(DOMAIN, "complete_sleep", handle_complete_sleep, schema=service_schema)

    hass.services.async_register(DOMAIN, "start_feeding", handle_start_feeding, schema=feeding_start_schema)
    hass.services.async_register(DOMAIN, "pause_feeding", handle_pause_feeding, schema=feeding_service_schema)
    hass.services.async_register(DOMAIN, "resume_feeding", handle_resume_feeding, schema=feeding_resume_schema)
    hass.services.async_register(DOMAIN, "switch_feeding_side", handle_switch_feeding_side, schema=feeding_service_schema)
    hass.services.async_register(DOMAIN, "cancel_feeding", handle_cancel_feeding, schema=feeding_service_schema)
    hass.services.async_register(DOMAIN, "complete_feeding", handle_complete_feeding, schema=feeding_service_schema)

    hass.services.async_register(DOMAIN, "log_diaper_pee", handle_log_diaper_pee, schema=diaper_pee_schema)
    hass.services.async_register(DOMAIN, "log_diaper_poo", handle_log_diaper_poo, schema=diaper_poo_schema)
    hass.services.async_register(DOMAIN, "log_diaper_both", handle_log_diaper_both, schema=diaper_both_schema)
    hass.services.async_register(DOMAIN, "log_diaper_dry", handle_log_diaper_dry, schema=diaper_dry_schema)

    hass.services.async_register(DOMAIN, "log_growth", handle_log_growth, schema=growth_schema)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop real-time listeners before unloading
    if entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coordinator:
            await coordinator.async_shutdown()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HuckleberryDataUpdateCoordinator(DataUpdateCoordinator[dict[str, ChildRealtimeData]]):
    """Class to manage fetching Huckleberry data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: HuckleberryAPI,
        children: list[ChildData],
    ) -> None:
        """Initialize."""
        self.api = api
        self.children = children
        self._realtime_data: dict[str, ChildRealtimeData] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),  # Fallback polling, listeners are primary
        )

    async def async_setup_listeners(self) -> None:
        """Set up real-time listeners for instant updates."""
        _LOGGER.info("Setting up real-time Firestore listeners")

        for child in self.children:
            child_uid = child["uid"]

            # Set up sleep listener
            def make_sleep_callback(uid):
                def callback(data):
                    """Handle real-time sleep updates."""
                    if uid not in self._realtime_data:
                        self._realtime_data[uid] = {"child": child}
                    self._realtime_data[uid]["sleep_status"] = data
                    # Trigger coordinator update
                    self.hass.loop.call_soon_threadsafe(
                        self.async_set_updated_data, dict(self._realtime_data)
                    )
                return callback

            await self.hass.async_add_executor_job(
                self.api.setup_realtime_listener, child_uid, make_sleep_callback(child_uid)
            )

            # Set up feed listener (for feeding tracking)
            def make_feed_callback(uid):
                def callback(data):
                    """Handle real-time feed updates."""
                    if uid not in self._realtime_data:
                        self._realtime_data[uid] = {"child": child}
                    self._realtime_data[uid]["feed_status"] = data
                    # Trigger coordinator update
                    self.hass.loop.call_soon_threadsafe(
                        self.async_set_updated_data, dict(self._realtime_data)
                    )
                return callback

            await self.hass.async_add_executor_job(
                self.api.setup_feed_listener, child_uid, make_feed_callback(child_uid)
            )

            # Set up health listener (for growth tracking)
            def make_health_callback(uid):
                def callback(data):
                    """Handle real-time health updates."""
                    if uid not in self._realtime_data:
                        self._realtime_data[uid] = {"child": child}

                    # Extract growth data from prefs.lastGrowthEntry
                    prefs = data.get("prefs", {})
                    last_growth = prefs.get("lastGrowthEntry", {})

                    _LOGGER.debug("Health data received for %s: has_prefs=%s, has_lastGrowthEntry=%s",
                                  uid, bool(prefs), bool(last_growth))

                    if last_growth:
                        growth_data: GrowthData = {
                            "weight": last_growth.get("weight"),
                            "height": last_growth.get("height"),
                            "head": last_growth.get("head"),
                            "weight_units": last_growth.get("weightUnits", "kg"),
                            "height_units": last_growth.get("heightUnits", "cm"),
                            "head_units": last_growth.get("headUnits", "hcm"),
                            "timestamp": last_growth.get("start"),
                        }
                        self._realtime_data[uid]["growth_data"] = growth_data
                        _LOGGER.debug("Updated growth data: weight=%s, height=%s, head=%s, timestamp=%s",
                                      growth_data.get("weight"), growth_data.get("height"),
                                      growth_data.get("head"), growth_data.get("timestamp"))
                    else:
                        # Set empty growth data if none exists
                        empty_growth: GrowthData = {
                            "weight_units": "kg",
                            "height_units": "cm",
                            "head_units": "hcm",
                        }
                        self._realtime_data[uid]["growth_data"] = empty_growth
                        _LOGGER.debug("No growth data found in health document")

                    # Trigger coordinator update
                    self.hass.loop.call_soon_threadsafe(
                        self.async_set_updated_data, dict(self._realtime_data)
                    )
                return callback

            await self.hass.async_add_executor_job(
                self.api.setup_health_listener, child_uid, make_health_callback(child_uid)
            )

            # Set up diaper listener (for diaper tracking)
            def make_diaper_callback(uid):
                def callback(data):
                    """Handle real-time diaper updates."""
                    if uid not in self._realtime_data:
                        self._realtime_data[uid] = {"child": child}
                    self._realtime_data[uid]["diaper_data"] = data
                    # Trigger coordinator update
                    self.hass.loop.call_soon_threadsafe(
                        self.async_set_updated_data, dict(self._realtime_data)
                    )
                return callback

            await self.hass.async_add_executor_job(
                self.api.setup_diaper_listener, child_uid, make_diaper_callback(child_uid)
            )

        _LOGGER.info("Real-time listeners active - updates will be instant!")

    async def _async_update_data(self) -> dict[str, ChildRealtimeData]:
        """Update data via library (fallback when listeners aren't active)."""
        # If we have real-time data, return it (listeners populate sleep, feed, health, diaper)
        if self._realtime_data:
            return dict(self._realtime_data)

        # Initial data structure - listeners will populate it
        # Don't fetch growth data here - the health listener handles it
        data: dict[str, ChildRealtimeData] = {}
        for child in self.children:
            child_uid = child["uid"]
            data[child_uid] = {
                "child": child,
                "sleep_status": {},
                # growth_data will be populated by health listener
            }

        return data

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and stop listeners."""
        _LOGGER.info("Shutting down Huckleberry coordinator")
        await self.hass.async_add_executor_job(self.api.stop_all_listeners)

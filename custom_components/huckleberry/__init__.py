"""Huckleberry Baby Sleep Tracker integration for Home Assistant."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import NotRequired, TypedDict, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from huckleberry_api import HuckleberryAPI
from huckleberry_api.firebase_types import FirebaseChildDocument, FirebaseUserChildRef
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR, Platform.CALENDAR]


# Type definitions for integration data structures
class ChildData(TypedDict, total=False):
    """Normalized child data used by the integration."""

    uid: str
    name: str
    birthday: str | int | float | None
    picture: str | None
    gender: str | None
    color: str | None
    created_at: int | float | None
    night_start: str | int | float | None
    morning_cutoff: str | int | float | None
    expected_naps: str | None
    categories: dict[str, bool] | None


class GrowthData(TypedDict, total=False):
    """Normalized growth data used by sensor entities."""

    weight: float | int | None
    height: float | int | None
    head: float | int | None
    weight_units: str
    height_units: str
    head_units: str
    timestamp: float | int | None


class RealtimeTimestamp(TypedDict, total=False):
    """Realtime timestamp data."""

    seconds: int | float


class LastSleepData(TypedDict, total=False):
    """Last sleep data from realtime prefs."""

    start: int | float
    duration: int | float


class SleepPrefsData(TypedDict, total=False):
    """Sleep preferences data."""

    lastSleep: LastSleepData


class SleepTimerData(TypedDict, total=False):
    """Realtime sleep timer data."""

    active: bool
    paused: bool
    timestamp: RealtimeTimestamp
    timerStartTime: int | float
    timerEndTime: int | float


class SleepStatusData(TypedDict, total=False):
    """Realtime sleep status payload."""

    timer: SleepTimerData
    prefs: SleepPrefsData
    last_updated: int | float
    sleep_duration: int | float
    sleep_start: int | float


class LastNursingData(TypedDict, total=False):
    """Last nursing data from realtime prefs."""

    start: int | float
    duration: int | float
    leftDuration: int | float
    rightDuration: int | float
    timestamp: int | float


class LastBottleData(TypedDict, total=False):
    """Last bottle data from realtime prefs."""

    start: int | float
    bottleAmount: int | float
    amount: int | float
    bottleUnits: str
    units: str
    bottleType: str
    offset: int


class LastSideData(TypedDict, total=False):
    """Last feeding side from realtime prefs."""

    lastSide: str


class FeedPrefsData(TypedDict, total=False):
    """Feed preferences data."""

    lastNursing: LastNursingData
    lastBottle: LastBottleData
    lastSide: LastSideData


class FeedTimerData(TypedDict, total=False):
    """Realtime feed timer data."""

    active: bool
    paused: bool
    feedStartTime: int | float
    leftDuration: int | float
    rightDuration: int | float
    lastSide: str
    activeSide: str
    timestamp: RealtimeTimestamp


class FeedStatusData(TypedDict, total=False):
    """Realtime feed status payload."""

    timer: FeedTimerData
    prefs: FeedPrefsData


class LastDiaperData(TypedDict, total=False):
    """Last diaper data from realtime prefs."""

    start: int | float
    mode: str
    offset: int


class DiaperPrefsData(TypedDict, total=False):
    """Diaper preferences data."""

    lastDiaper: LastDiaperData


class DiaperData(TypedDict, total=False):
    """Realtime diaper payload."""

    prefs: DiaperPrefsData


class LastGrowthEntryData(TypedDict, total=False):
    """Last growth entry from realtime health data."""

    weight: int | float
    height: int | float
    head: int | float
    weightUnits: str
    heightUnits: str
    headUnits: str
    start: int | float


class HealthPrefsData(TypedDict, total=False):
    """Health preferences data."""

    lastGrowthEntry: LastGrowthEntryData


class HealthData(TypedDict, total=False):
    """Realtime health payload."""

    prefs: HealthPrefsData


class HuckleberryEntryData(TypedDict):
    """Data stored in hass.data[DOMAIN][entry.entry_id]."""

    api: HuckleberryAPI
    coordinator: "HuckleberryDataUpdateCoordinator"
    children: list[ChildData]


class ChildRealtimeData(TypedDict):
    """Real-time data structure for a single child."""

    child: ChildData
    sleep_status: NotRequired[SleepStatusData]
    feed_status: NotRequired[FeedStatusData]
    growth_data: NotRequired[GrowthData]
    diaper_data: NotRequired[DiaperData]


def _normalize_model_data(data: object) -> object:
    """Normalize API model instances to plain dictionaries."""
    if isinstance(data, dict):
        return data

    model_dump = getattr(data, "model_dump", None)
    if callable(model_dump):
        normalized = model_dump(by_alias=True, exclude_none=True)
        if isinstance(normalized, dict):
            return normalized

    return {}


def _normalize_sleep_status(data: object) -> SleepStatusData:
    """Normalize realtime sleep payloads to the local typed structure."""
    return cast(SleepStatusData, _normalize_model_data(data))


def _normalize_feed_status(data: object) -> FeedStatusData:
    """Normalize realtime feed payloads to the local typed structure."""
    return cast(FeedStatusData, _normalize_model_data(data))


def _normalize_diaper_data(data: object) -> DiaperData:
    """Normalize realtime diaper payloads to the local typed structure."""
    return cast(DiaperData, _normalize_model_data(data))


def _normalize_health_data(data: object) -> HealthData:
    """Normalize realtime health payloads to the local typed structure."""
    return cast(HealthData, _normalize_model_data(data))


def _normalize_child_data(
    child_ref: FirebaseUserChildRef, child_doc: FirebaseChildDocument | None
) -> ChildData:
    """Normalize API child documents to the integration child structure."""
    child_uid = child_ref.cid
    name = (child_doc.childsName if child_doc else None) or child_ref.nickname or child_uid
    return {
        "uid": child_uid,
        "name": name,
        "birthday": child_doc.birthdate if child_doc else None,
        "picture": (child_doc.picture if child_doc else None) or child_ref.picture,
        "gender": child_doc.gender if child_doc else None,
        "color": (child_doc.color if child_doc else None) or child_ref.color,
        "created_at": child_doc.createdAt if child_doc else None,
        "night_start": child_doc.nightStart if child_doc else None,
        "morning_cutoff": child_doc.morningCutoff if child_doc else None,
        "expected_naps": child_doc.naps if child_doc else None,
        "categories": child_doc.categories if child_doc else None,
    }


async def _async_get_children(api: HuckleberryAPI) -> list[ChildData]:
    """Fetch and normalize all children for the authenticated user."""
    user = await api.get_user()
    if user is None:
        return []

    child_docs = await asyncio.gather(
        *(api.get_child(child_ref.cid) for child_ref in user.childList),
        return_exceptions=True,
    )

    normalized_children: list[ChildData] = []
    for child_ref, child_doc in zip(user.childList, child_docs, strict=True):
        if isinstance(child_doc, Exception):
            _LOGGER.warning(
                "Failed to fetch child document for %s: %s. Falling back to user profile data.",
                child_ref.cid,
                child_doc,
            )
            normalized_children.append(_normalize_child_data(child_ref, None))
            continue

        normalized_children.append(_normalize_child_data(child_ref, child_doc))

    return normalized_children


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Huckleberry from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = HuckleberryAPI(
        email=entry.data["email"],
        password=entry.data["password"],
        timezone=str(hass.config.time_zone),
        websession=async_get_clientsession(hass),
    )

    # Authenticate
    try:
        await api.authenticate()
    except Exception as err:
        _LOGGER.error("Failed to authenticate with Huckleberry: %s", err)
        return False

    # Get children
    try:
        children = await _async_get_children(api)
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
        await method(target_child)
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
        await api.start_nursing(child_uid, side)

    async def handle_pause_feeding(call):
        await _call_api("pause_nursing", call)

    async def handle_resume_feeding(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        side = call.data.get("side")  # Optional side parameter
        _LOGGER.info("Resuming feeding for child %s on %s", child_uid, side if side else "current side")
        await api.resume_nursing(child_uid, side)

    async def handle_switch_feeding_side(call):
        await _call_api("switch_nursing_side", call)

    async def handle_cancel_feeding(call):
        await _call_api("cancel_nursing", call)

    async def handle_complete_feeding(call):
        await _call_api("complete_nursing", call)

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
        await api.log_diaper(child_uid, "pee", pee_amount, None, None, None, diaper_rash, notes)

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
        await api.log_diaper(child_uid, "poo", None, poo_amount, color, consistency, diaper_rash, notes)

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
        await api.log_diaper(child_uid, "both", pee_amount, poo_amount, color, consistency, diaper_rash, notes)

    async def handle_log_diaper_dry(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        diaper_rash = call.data.get("diaper_rash", False)
        notes = call.data.get("notes")
        _LOGGER.info("Logging dry diaper check for child %s", child_uid)
        await api.log_diaper(child_uid, "dry", None, None, None, None, diaper_rash, notes)

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
        await api.log_growth(child_uid, weight, height, head, units)
        # Refresh coordinator to update growth sensor
        coordinator: HuckleberryDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_request_refresh()

    async def handle_log_bottle(call):
        api: HuckleberryAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        child_uid = _get_child_uid_from_call(call)
        if not child_uid:
            _LOGGER.error("No child_uid could be determined from service call")
            return
        amount = call.data.get("amount")
        bottle_type = call.data.get("bottle_type")
        units = call.data.get("units", "ml")
        _LOGGER.info("Logging bottle feeding for child %s (amount=%s %s, type=%s)",
                     child_uid, amount, units, bottle_type)
        await api.log_bottle(child_uid, amount, bottle_type, units)

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

    bottle_schema = vol.Schema({
        vol.Required("device_id"): cv.string,
        vol.Optional("child_uid"): cv.string,
        vol.Required("amount"): vol.Coerce(float),
        vol.Required("bottle_type"): vol.In([
            "Formula",
            "Breast Milk",
            "Tube Feeding",
            "Cow Milk",
            "Goat Milk",
            "Soy Milk",
            "Other",
        ]),
        vol.Optional("units"): vol.In(["oz", "ml"]),
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
    hass.services.async_register(DOMAIN, "log_bottle", handle_log_bottle, schema=bottle_schema)

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
            def make_sleep_callback(uid: str, child_data: ChildData):
                def callback(data):
                    """Handle real-time sleep updates."""
                    if uid not in self._realtime_data:
                        self._realtime_data[uid] = {"child": child_data}
                    self._realtime_data[uid]["sleep_status"] = _normalize_sleep_status(data)
                    # Trigger coordinator update
                    self.hass.loop.call_soon_threadsafe(
                        self.async_set_updated_data, dict(self._realtime_data)
                    )
                return callback

            await self.api.setup_sleep_listener(child_uid, make_sleep_callback(child_uid, child))

            # Set up feed listener (for feeding tracking)
            def make_feed_callback(uid: str, child_data: ChildData):
                def callback(data):
                    """Handle real-time feed updates."""
                    if uid not in self._realtime_data:
                        self._realtime_data[uid] = {"child": child_data}
                    self._realtime_data[uid]["feed_status"] = _normalize_feed_status(data)
                    # Trigger coordinator update
                    self.hass.loop.call_soon_threadsafe(
                        self.async_set_updated_data, dict(self._realtime_data)
                    )
                return callback

            await self.api.setup_feed_listener(child_uid, make_feed_callback(child_uid, child))

            # Set up health listener (for growth tracking)
            def make_health_callback(uid: str, child_data: ChildData):
                def callback(data):
                    """Handle real-time health updates."""
                    if uid not in self._realtime_data:
                        self._realtime_data[uid] = {"child": child_data}

                    health_data = _normalize_health_data(data)
                    # Extract growth data from prefs.lastGrowthEntry
                    prefs = health_data.get("prefs")
                    last_growth = prefs.get("lastGrowthEntry") if prefs else None

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

            await self.api.setup_health_listener(child_uid, make_health_callback(child_uid, child))

            # Set up diaper listener (for diaper tracking)
            def make_diaper_callback(uid: str, child_data: ChildData):
                def callback(data):
                    """Handle real-time diaper updates."""
                    if uid not in self._realtime_data:
                        self._realtime_data[uid] = {"child": child_data}
                    self._realtime_data[uid]["diaper_data"] = _normalize_diaper_data(data)
                    # Trigger coordinator update
                    self.hass.loop.call_soon_threadsafe(
                        self.async_set_updated_data, dict(self._realtime_data)
                    )
                return callback

            await self.api.setup_diaper_listener(child_uid, make_diaper_callback(child_uid, child))

        _LOGGER.info("Real-time listeners active - updates will be instant!")

    async def _async_update_data(self) -> dict[str, ChildRealtimeData]:
        """Update data via library (fallback when listeners aren't active)."""
        # Ensure session is valid (refresh token if needed) to keep listeners alive
        try:
            await self.api.ensure_session()
        except Exception as err:
            _LOGGER.error("Failed to maintain Huckleberry session: %s", err)

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
        await self.api.stop_all_listeners()

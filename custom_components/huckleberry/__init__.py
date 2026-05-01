"""Huckleberry integration for Home Assistant."""
from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import timedelta
from typing import Final, Literal, TypedDict, cast, get_args

import voluptuous as vol
from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from huckleberry_api import HuckleberryAPI
from huckleberry_api.firebase_types import (
    BottleType,
    FeedSide,
    FirebaseChildDocument,
    FirebaseDiaperDocumentData,
    FirebaseFeedDocumentData,
    FirebaseHealthDocumentData,
    FirebaseSleepDocumentData,
    FirebaseUserDocument,
    PooColor,
    PooConsistency,
)

from .const import DOMAIN
from .models import HuckleberryChildProfile, HuckleberryChildState

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final[list[Platform]] = [Platform.SWITCH, Platform.SENSOR, Platform.CALENDAR]
SERVICE_CHILD_SCHEMA: Final = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
    }
)
FEED_SIDE_OPTIONS: Final[tuple[str, ...]] = tuple(
    side for side in get_args(FeedSide) if side != "none"
)
POO_COLOR_OPTIONS: Final[tuple[str, ...]] = tuple(get_args(PooColor))
POO_CONSISTENCY_OPTIONS: Final[tuple[str, ...]] = tuple(get_args(PooConsistency))
BOTTLE_TYPE_LABELS: Final[dict[str, BottleType]] = {
    "formula": "Formula",
    "breast_milk": "Breast Milk",
    "tube_feeding": "Tube Feeding",
    "cow_milk": "Cow Milk",
    "goat_milk": "Goat Milk",
    "soy_milk": "Soy Milk",
    "other": "Other",
}
BOTTLE_TYPE_OPTIONS: Final[tuple[str, ...]] = tuple(BOTTLE_TYPE_LABELS)
BOTTLE_TYPE_LEGACY_OPTIONS: Final[tuple[str, ...]] = tuple(get_args(BottleType))
DiaperAmount = Literal["little", "medium", "big"]
GrowthUnits = Literal["metric", "imperial"]
BottleUnits = Literal["ml", "oz"]


class HuckleberryEntryData(TypedDict):
    """Stored config-entry data."""

    api: HuckleberryAPI
    coordinator: "HuckleberryDataUpdateCoordinator"
    children: list[HuckleberryChildProfile]


async def _async_load_children(api: HuckleberryAPI) -> list[HuckleberryChildProfile]:
    """Load all children for the authenticated user."""
    user = await api.get_user()
    if user is None:
        return []

    return await _async_load_child_profiles(api, user)


async def _async_load_child_profiles(
    api: HuckleberryAPI,
    user: FirebaseUserDocument,
) -> list[HuckleberryChildProfile]:
    """Resolve user child references to full child documents."""
    child_documents = await asyncio.gather(
        *(api.get_child(child_ref.cid) for child_ref in user.childList)
    )

    profiles: list[HuckleberryChildProfile] = []
    for child_ref, child_document in zip(user.childList, child_documents, strict=True):
        if child_document is None:
            _LOGGER.warning("Child document not found for %s", child_ref.cid)
            continue

        profiles.append(
            HuckleberryChildProfile(
                uid=child_ref.cid,
                reference=child_ref,
                document=child_document,
            )
        )

    return profiles


async def _async_prune_orphaned_child_registry_entries(
    hass: HomeAssistant,
    entry: ConfigEntry,
    children: list[HuckleberryChildProfile],
) -> None:
    """Remove stale child entities and devices no longer present upstream."""
    current_child_uids = {child.uid for child in children}
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        child_identifiers = {
            identifier_value
            for identifier_domain, identifier_value in device.identifiers
            if identifier_domain == DOMAIN
        }
        if not child_identifiers or not child_identifiers.isdisjoint(current_child_uids):
            continue

        _LOGGER.info(
            "Removing orphaned Huckleberry child device %s (%s)",
            device.name_by_user or device.name or device.id,
            ", ".join(sorted(child_identifiers)),
        )

        for entity_entry in er.async_entries_for_device(
            entity_registry,
            device.id,
            include_disabled_entities=True,
        ):
            if entity_entry.config_entry_id == entry.entry_id:
                entity_registry.async_remove(entity_entry.entity_id)

        device_registry.async_remove_device(device.id)


def _get_child_uid_from_call(
    hass: HomeAssistant,
    call: ServiceCall,
) -> str:
    """Extract the child UID from service call data.

    Raises ServiceValidationError when the device_id cannot be resolved to a child.
    """
    device_id = call.data.get(CONF_DEVICE_ID)
    if isinstance(device_id, str):
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device is not None:
            for identifier_domain, identifier_value in device.identifiers:
                if identifier_domain == DOMAIN:
                    return identifier_value

    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="invalid_child_device",
    )


def _string_value(value: object) -> str | None:
    """Return a string value when present."""
    return value if isinstance(value, str) else None


def _feed_side_value(value: object, *, default: FeedSide | None = None) -> FeedSide | None:
    """Return a validated feed-side literal from service data."""
    string_value = _string_value(value)
    if string_value is None:
        return default
    return cast(FeedSide, string_value)


def _diaper_amount_value(value: object) -> DiaperAmount | None:
    """Return a validated diaper amount literal from service data."""
    string_value = _string_value(value)
    return cast(DiaperAmount | None, string_value)


def _poo_color_value(value: object) -> PooColor | None:
    """Return a validated poo color literal from service data."""
    string_value = _string_value(value)
    return cast(PooColor | None, string_value)


def _poo_consistency_value(value: object) -> PooConsistency | None:
    """Return a validated poo consistency literal from service data."""
    string_value = _string_value(value)
    return cast(PooConsistency | None, string_value)


def _growth_units_value(value: object) -> GrowthUnits:
    """Return a validated growth units literal from service data."""
    string_value = _string_value(value)
    if string_value is None:
        return "metric"
    return cast(GrowthUnits, string_value)


def _bottle_units_value(value: object) -> BottleUnits:
    """Return a validated bottle units literal from service data."""
    string_value = _string_value(value)
    if string_value is None:
        return "ml"
    return cast(BottleUnits, string_value)


def _api_bottle_type(value: str | None) -> BottleType:
    """Normalize bottle type values to the API's expected literals."""
    if value is None:
        return "Formula"

    return BOTTLE_TYPE_LABELS.get(value, cast(BottleType, value))


def _build_service_method_schema(
    *,
    include_side: bool = False,
    include_growth: bool = False,
    include_bottle: bool = False,
    include_diaper_fields: bool = False,
    include_potty_fields: bool = False,
) -> vol.Schema:
    """Create a service schema from the shared target fields."""
    schema: dict[object, object] = {
        vol.Required(CONF_DEVICE_ID): cv.string,
    }

    if include_side:
        schema[vol.Optional("side")] = vol.In(FEED_SIDE_OPTIONS)
    if include_growth:
        schema[vol.Optional("weight")] = vol.Coerce(float)
        schema[vol.Optional("height")] = vol.Coerce(float)
        schema[vol.Optional("head")] = vol.Coerce(float)
        schema[vol.Optional("units", default="metric")] = vol.In(("metric", "imperial"))
    if include_bottle:
        schema[vol.Required("amount")] = vol.Coerce(float)
        schema[vol.Required("bottle_type")] = vol.In(
            BOTTLE_TYPE_OPTIONS + BOTTLE_TYPE_LEGACY_OPTIONS
        )
        schema[vol.Optional("units", default="ml")] = vol.In(("ml", "oz"))
    if include_diaper_fields:
        schema[vol.Optional("pee_amount")] = vol.In(("little", "medium", "big"))
        schema[vol.Optional("poo_amount")] = vol.In(("little", "medium", "big"))
        schema[vol.Optional("color")] = vol.In(POO_COLOR_OPTIONS)
        schema[vol.Optional("consistency")] = vol.In(POO_CONSISTENCY_OPTIONS)
        schema[vol.Optional("diaper_rash", default=False)] = cv.boolean
        schema[vol.Optional("notes")] = cv.string
    if include_potty_fields:
        schema[vol.Optional("pee_amount")] = vol.In(("little", "medium", "big"))
        schema[vol.Optional("poo_amount")] = vol.In(("little", "medium", "big"))
        schema[vol.Optional("color")] = vol.In(POO_COLOR_OPTIONS)
        schema[vol.Optional("consistency")] = vol.In(POO_CONSISTENCY_OPTIONS)
        schema[vol.Optional("how_it_happened")] = vol.In(["wentPotty", "accident", "satButDry"])
        schema[vol.Optional("notes")] = cv.string

    return vol.Schema(schema)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Huckleberry from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = HuckleberryAPI(
        email=entry.data["email"],
        password=entry.data["password"],
        timezone=str(hass.config.time_zone),
        websession=async_get_clientsession(hass),
    )

    try:
        await api.authenticate()
        children = await _async_load_children(api)
    except ClientError as err:
        _LOGGER.error("Failed to authenticate with Huckleberry: %s", err)
        return False
    except Exception as err:
        _LOGGER.error("Failed to initialize Huckleberry API: %s", err)
        return False

    await _async_prune_orphaned_child_registry_entries(hass, entry, children)

    if not children:
        _LOGGER.error("No children found in Huckleberry account")
        return False

    coordinator = HuckleberryDataUpdateCoordinator(hass, api, children)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_setup_listeners()

    entry_data: HuckleberryEntryData = {
        "api": api,
        "coordinator": coordinator,
        "children": children,
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry_data = cast(HuckleberryEntryData, hass.data[DOMAIN][entry.entry_id])
    api_client = entry_data["api"]

    def _target_child(call: ServiceCall) -> str:
        return _get_child_uid_from_call(hass, call)

    async def handle_start_sleep(call: ServiceCall) -> None:
        await api_client.start_sleep(_target_child(call))

    async def handle_pause_sleep(call: ServiceCall) -> None:
        await api_client.pause_sleep(_target_child(call))

    async def handle_resume_sleep(call: ServiceCall) -> None:
        await api_client.resume_sleep(_target_child(call))

    async def handle_cancel_sleep(call: ServiceCall) -> None:
        await api_client.cancel_sleep(_target_child(call))

    async def handle_complete_sleep(call: ServiceCall) -> None:
        await api_client.complete_sleep(_target_child(call))

    async def handle_start_nursing(call: ServiceCall) -> None:
        await api_client.start_nursing(
            _target_child(call),
            _feed_side_value(call.data.get("side"), default="left") or "left",
        )

    async def handle_pause_nursing(call: ServiceCall) -> None:
        await api_client.pause_nursing(_target_child(call))

    async def handle_resume_nursing(call: ServiceCall) -> None:
        await api_client.resume_nursing(
            _target_child(call),
            _feed_side_value(call.data.get("side")),
        )

    async def handle_switch_nursing_side(call: ServiceCall) -> None:
        await api_client.switch_nursing_side(_target_child(call))

    async def handle_cancel_nursing(call: ServiceCall) -> None:
        await api_client.cancel_nursing(_target_child(call))

    async def handle_complete_nursing(call: ServiceCall) -> None:
        await api_client.complete_nursing(_target_child(call))

    async def handle_log_diaper_pee(call: ServiceCall) -> None:
        await api_client.log_diaper(
            _target_child(call),
            start_time=dt_util.now(),
            mode="pee",
            pee_amount=_diaper_amount_value(call.data.get("pee_amount")),
            diaper_rash=bool(call.data.get("diaper_rash", False)),
            notes=_string_value(call.data.get("notes")),
        )

    async def handle_log_diaper_poo(call: ServiceCall) -> None:
        await api_client.log_diaper(
            _target_child(call),
            start_time=dt_util.now(),
            mode="poo",
            poo_amount=_diaper_amount_value(call.data.get("poo_amount")),
            color=_poo_color_value(call.data.get("color")),
            consistency=_poo_consistency_value(call.data.get("consistency")),
            diaper_rash=bool(call.data.get("diaper_rash", False)),
            notes=_string_value(call.data.get("notes")),
        )

    async def handle_log_diaper_both(call: ServiceCall) -> None:
        await api_client.log_diaper(
            _target_child(call),
            start_time=dt_util.now(),
            mode="both",
            pee_amount=_diaper_amount_value(call.data.get("pee_amount")),
            poo_amount=_diaper_amount_value(call.data.get("poo_amount")),
            color=_poo_color_value(call.data.get("color")),
            consistency=_poo_consistency_value(call.data.get("consistency")),
            diaper_rash=bool(call.data.get("diaper_rash", False)),
            notes=_string_value(call.data.get("notes")),
        )

    async def handle_log_diaper_dry(call: ServiceCall) -> None:
        await api_client.log_diaper(
            _target_child(call),
            start_time=dt_util.now(),
            mode="dry",
            diaper_rash=bool(call.data.get("diaper_rash", False)),
            notes=_string_value(call.data.get("notes")),
        )

    async def handle_log_potty_pee(call: ServiceCall) -> None:
        await api_client.log_potty(
            _target_child(call),
            start_time=dt_util.now(),
            mode="pee",
            pee_amount=_diaper_amount_value(call.data.get("pee_amount")),
            how_it_happened=call.data.get("how_it_happened", "wentPotty"),
            notes=_string_value(call.data.get("notes")),
        )

    async def handle_log_potty_poo(call: ServiceCall) -> None:
        await api_client.log_potty(
            _target_child(call),
            start_time=dt_util.now(),
            mode="poo",
            poo_amount=_diaper_amount_value(call.data.get("poo_amount")),
            color=_poo_color_value(call.data.get("color")),
            consistency=_poo_consistency_value(call.data.get("consistency")),
            how_it_happened=call.data.get("how_it_happened", "wentPotty"),
            notes=_string_value(call.data.get("notes")),
        )

    async def handle_log_potty_both(call: ServiceCall) -> None:
        await api_client.log_potty(
            _target_child(call),
            start_time=dt_util.now(),
            mode="both",
            pee_amount=_diaper_amount_value(call.data.get("pee_amount")),
            poo_amount=_diaper_amount_value(call.data.get("poo_amount")),
            color=_poo_color_value(call.data.get("color")),
            consistency=_poo_consistency_value(call.data.get("consistency")),
            how_it_happened=call.data.get("how_it_happened", "wentPotty"),
            notes=_string_value(call.data.get("notes")),
        )

    async def handle_log_potty_dry(call: ServiceCall) -> None:
        await api_client.log_potty(
            _target_child(call),
            start_time=dt_util.now(),
            mode="dry",
            how_it_happened="satButDry",
            notes=_string_value(call.data.get("notes")),
        )

    async def handle_log_growth(call: ServiceCall) -> None:
        await api_client.log_growth(
            _target_child(call),
            start_time=dt_util.now(),
            weight=cast(float | None, call.data.get("weight")),
            height=cast(float | None, call.data.get("height")),
            head=cast(float | None, call.data.get("head")),
            units=_growth_units_value(call.data.get("units")),
        )
        await coordinator.async_request_refresh()

    async def handle_log_bottle(call: ServiceCall) -> None:
        await api_client.log_bottle(
            _target_child(call),
            start_time=dt_util.now(),
            amount=cast(float, call.data["amount"]),
            bottle_type=_api_bottle_type(_string_value(call.data.get("bottle_type"))),
            units=_bottle_units_value(call.data.get("units")),
        )

    hass.services.async_register(DOMAIN, "start_sleep", handle_start_sleep, schema=SERVICE_CHILD_SCHEMA)
    hass.services.async_register(DOMAIN, "pause_sleep", handle_pause_sleep, schema=SERVICE_CHILD_SCHEMA)
    hass.services.async_register(DOMAIN, "resume_sleep", handle_resume_sleep, schema=SERVICE_CHILD_SCHEMA)
    hass.services.async_register(DOMAIN, "cancel_sleep", handle_cancel_sleep, schema=SERVICE_CHILD_SCHEMA)
    hass.services.async_register(DOMAIN, "complete_sleep", handle_complete_sleep, schema=SERVICE_CHILD_SCHEMA)

    nursing_schema = _build_service_method_schema(include_side=True)
    hass.services.async_register(DOMAIN, "start_nursing", handle_start_nursing, schema=nursing_schema)
    hass.services.async_register(DOMAIN, "pause_nursing", handle_pause_nursing, schema=SERVICE_CHILD_SCHEMA)
    hass.services.async_register(DOMAIN, "resume_nursing", handle_resume_nursing, schema=nursing_schema)
    hass.services.async_register(DOMAIN, "switch_nursing_side", handle_switch_nursing_side, schema=SERVICE_CHILD_SCHEMA)
    hass.services.async_register(DOMAIN, "cancel_nursing", handle_cancel_nursing, schema=SERVICE_CHILD_SCHEMA)
    hass.services.async_register(DOMAIN, "complete_nursing", handle_complete_nursing, schema=SERVICE_CHILD_SCHEMA)

    diaper_schema = _build_service_method_schema(include_diaper_fields=True)
    hass.services.async_register(DOMAIN, "log_diaper_pee", handle_log_diaper_pee, schema=diaper_schema)
    hass.services.async_register(DOMAIN, "log_diaper_poo", handle_log_diaper_poo, schema=diaper_schema)
    hass.services.async_register(DOMAIN, "log_diaper_both", handle_log_diaper_both, schema=diaper_schema)
    hass.services.async_register(DOMAIN, "log_diaper_dry", handle_log_diaper_dry, schema=diaper_schema)

    potty_schema = _build_service_method_schema(include_potty_fields=True)
    hass.services.async_register(DOMAIN, "log_potty_pee", handle_log_potty_pee, schema=potty_schema)
    hass.services.async_register(DOMAIN, "log_potty_poo", handle_log_potty_poo, schema=potty_schema)
    hass.services.async_register(DOMAIN, "log_potty_both", handle_log_potty_both, schema=potty_schema)
    hass.services.async_register(DOMAIN, "log_potty_dry", handle_log_potty_dry, schema=potty_schema)

    hass.services.async_register(
        DOMAIN,
        "log_growth",
        handle_log_growth,
        schema=_build_service_method_schema(include_growth=True),
    )
    hass.services.async_register(
        DOMAIN,
        "log_bottle",
        handle_log_bottle,
        schema=_build_service_method_schema(include_bottle=True),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data[DOMAIN]:
        coordinator = cast(HuckleberryEntryData, hass.data[DOMAIN][entry.entry_id]).get("coordinator")
        if isinstance(coordinator, HuckleberryDataUpdateCoordinator):
            await coordinator.async_shutdown()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HuckleberryDataUpdateCoordinator(DataUpdateCoordinator[dict[str, HuckleberryChildState]]):
    """Coordinator that keeps session state alive and stores realtime documents."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: HuckleberryAPI,
        children: list[HuckleberryChildProfile],
    ) -> None:
        self.api = api
        self.children = children
        self._realtime_data: dict[str, HuckleberryChildState] = {
            child.uid: HuckleberryChildState(profile=child) for child in children
        }
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    async def async_setup_listeners(self) -> None:
        """Set up realtime listeners for all tracked child documents."""
        for child in self.children:
            child_uid = child.uid

            def sleep_callback(data: FirebaseSleepDocumentData, uid: str = child_uid) -> None:
                self._realtime_data[uid].sleep_status = data
                self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, dict(self._realtime_data))

            def feed_callback(data: FirebaseFeedDocumentData, uid: str = child_uid) -> None:
                self._realtime_data[uid].feed_status = data
                self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, dict(self._realtime_data))

            def health_callback(data: FirebaseHealthDocumentData, uid: str = child_uid) -> None:
                self._realtime_data[uid].health_status = data
                self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, dict(self._realtime_data))

            def diaper_callback(data: FirebaseDiaperDocumentData, uid: str = child_uid) -> None:
                self._realtime_data[uid].diaper_status = data
                self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, dict(self._realtime_data))

            def child_callback(data: FirebaseChildDocument, uid: str = child_uid) -> None:
                self._realtime_data[uid].child_document = data
                self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, dict(self._realtime_data))

            await self.api.setup_sleep_listener(child_uid, sleep_callback)
            await self.api.setup_feed_listener(child_uid, feed_callback)
            await self.api.setup_health_listener(child_uid, health_callback)
            await self.api.setup_diaper_listener(child_uid, diaper_callback)
            await self.api.setup_child_listener(child_uid, child_callback)

    async def _async_update_data(self) -> dict[str, HuckleberryChildState]:
        """Refresh auth/session state while listeners provide live data."""
        await self.api.ensure_session()
        return dict(self._realtime_data)

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and stop active listeners."""
        await self.api.stop_all_listeners()
        await _async_close_api_firestore_clients(self.api)

    def get_state(self, child_uid: str) -> HuckleberryChildState | None:
        """Return the tracked state for a child."""
        return self.data.get(child_uid)

    def get_sleep_status(self, child_uid: str) -> FirebaseSleepDocumentData | None:
        """Return the current sleep document for a child."""
        state = self.get_state(child_uid)
        return state.sleep_status if state is not None else None

    def get_feed_status(self, child_uid: str) -> FirebaseFeedDocumentData | None:
        """Return the current feed document for a child."""
        state = self.get_state(child_uid)
        return state.feed_status if state is not None else None

    def get_health_status(self, child_uid: str) -> FirebaseHealthDocumentData | None:
        """Return the current health document for a child."""
        state = self.get_state(child_uid)
        return state.health_status if state is not None else None

    def get_diaper_status(self, child_uid: str) -> FirebaseDiaperDocumentData | None:
        """Return the current diaper document for a child."""
        state = self.get_state(child_uid)
        return state.diaper_status if state is not None else None

    def get_child_document(self, child_uid: str) -> FirebaseChildDocument | None:
        """Return the current child document for a child."""
        state = self.get_state(child_uid)
        return state.child_document if state is not None else None

async def _async_close_api_firestore_clients(api: HuckleberryAPI) -> None:
    """Close Firestore transports held by the API client.

    The upstream API stops listeners but leaves gRPC transports alive. In tests
    and on config-entry unload, that can leave background polling threads behind.
    """

    async def _async_close_transport(client: object | None) -> None:
        if client is None:
            return

        firestore_api = getattr(client, "_firestore_api", None)
        transport = getattr(firestore_api, "transport", None)
        close = getattr(transport, "close", None)
        if not callable(close):
            return

        result = close()
        if inspect.isawaitable(result):
            await result

    await _async_close_transport(getattr(api, "_firestore_client", None))
    await _async_close_transport(getattr(api, "_listener_client", None))

    if hasattr(api, "_firestore_client"):
        api._firestore_client = None
    if hasattr(api, "_firestore_client_loop"):
        api._firestore_client_loop = None
    if hasattr(api, "_listener_client"):
        api._listener_client = None


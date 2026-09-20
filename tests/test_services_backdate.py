"""Tests for backdated sleep and bottle service fields."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.huckleberry.const import DOMAIN

CHILD_UID = "test_child_uid"
# A fixed offset zone keeps the naive-localisation assertions independent of DST.
TEST_TIME_ZONE = "Etc/GMT+5"
TEST_UTC_OFFSET = timedelta(hours=-5)


async def _setup(hass: HomeAssistant, mock_huckleberry_api) -> dr.DeviceEntry:
    """Set up the integration against the mock API and return a targetable device."""
    await hass.config.async_set_time_zone(TEST_TIME_ZONE)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "test_password"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.huckleberry.HuckleberryAPI",
        return_value=mock_huckleberry_api,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    return device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, CHILD_UID)},
        name="Test Child",
    )


async def test_start_sleep_accepts_naive_start_time(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """A naive wall-clock value is read in Home Assistant's configured timezone."""
    device = await _setup(hass, mock_huckleberry_api)

    await hass.services.async_call(
        DOMAIN,
        "start_sleep",
        {"device_id": device.id, "start_time": "2026-09-19 07:30:00"},
        blocking=True,
    )

    start_time = mock_huckleberry_api.start_sleep.call_args.kwargs["start_time"]
    assert start_time.utcoffset() == TEST_UTC_OFFSET
    assert start_time.replace(tzinfo=None) == datetime(2026, 9, 19, 7, 30)


async def test_start_sleep_accepts_aware_start_time(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """An aware value keeps its instant and is handed over as an aware datetime."""
    device = await _setup(hass, mock_huckleberry_api)

    await hass.services.async_call(
        DOMAIN,
        "start_sleep",
        {"device_id": device.id, "start_time": "2026-09-19T12:30:00+00:00"},
        blocking=True,
    )

    start_time = mock_huckleberry_api.start_sleep.call_args.kwargs["start_time"]
    assert start_time.tzinfo is not None
    assert start_time == datetime(2026, 9, 19, 12, 30, tzinfo=timezone.utc)
    # Normalised to local, which for this zone is 07:30.
    assert start_time.replace(tzinfo=None) == datetime(2026, 9, 19, 7, 30)


async def test_start_sleep_without_start_time_is_unchanged(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """Omitting the field leaves the library to use its own default."""
    device = await _setup(hass, mock_huckleberry_api)

    await hass.services.async_call(DOMAIN, "start_sleep", {"device_id": device.id}, blocking=True)

    mock_huckleberry_api.start_sleep.assert_called_with(CHILD_UID, start_time=None)


async def test_complete_sleep_accepts_end_time(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """complete_sleep forwards end_time as an aware datetime."""
    device = await _setup(hass, mock_huckleberry_api)

    await hass.services.async_call(
        DOMAIN,
        "complete_sleep",
        {"device_id": device.id, "end_time": "2026-09-19 08:45:00"},
        blocking=True,
    )

    end_time = mock_huckleberry_api.complete_sleep.call_args.kwargs["end_time"]
    assert end_time.utcoffset() == TEST_UTC_OFFSET
    assert end_time.replace(tzinfo=None) == datetime(2026, 9, 19, 8, 45)


async def test_complete_sleep_without_end_time_is_unchanged(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """Omitting the field leaves the library to use its own default."""
    device = await _setup(hass, mock_huckleberry_api)

    await hass.services.async_call(DOMAIN, "complete_sleep", {"device_id": device.id}, blocking=True)

    mock_huckleberry_api.complete_sleep.assert_called_with(CHILD_UID, end_time=None)


async def test_set_sleep_start_time_forwards_value(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """The new service passes the child and an aware start time positionally."""
    device = await _setup(hass, mock_huckleberry_api)

    await hass.services.async_call(
        DOMAIN,
        "set_sleep_start_time",
        {"device_id": device.id, "start_time": "2026-09-19 07:05:00"},
        blocking=True,
    )

    child_uid, start_time = mock_huckleberry_api.set_sleep_start_time.call_args.args
    assert child_uid == CHILD_UID
    assert start_time.utcoffset() == TEST_UTC_OFFSET
    assert start_time.replace(tzinfo=None) == datetime(2026, 9, 19, 7, 5)


async def test_set_sleep_start_time_requires_start_time(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """start_time is required, so the schema rejects a call without it."""
    device = await _setup(hass, mock_huckleberry_api)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, "set_sleep_start_time", {"device_id": device.id}, blocking=True
        )

    mock_huckleberry_api.set_sleep_start_time.assert_not_called()


async def test_log_bottle_accepts_start_time(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """log_bottle uses the supplied time instead of now."""
    device = await _setup(hass, mock_huckleberry_api)

    await hass.services.async_call(
        DOMAIN,
        "log_bottle",
        {
            "device_id": device.id,
            "amount": 120.0,
            "bottle_type": "formula",
            "start_time": "2026-09-19 06:15:00",
        },
        blocking=True,
    )

    start_time = mock_huckleberry_api.log_bottle.call_args.kwargs["start_time"]
    assert start_time.utcoffset() == TEST_UTC_OFFSET
    assert start_time.replace(tzinfo=None) == datetime(2026, 9, 19, 6, 15)


async def test_log_bottle_without_start_time_uses_now(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """Omitting the field keeps the previous "now" behaviour."""
    device = await _setup(hass, mock_huckleberry_api)

    await hass.services.async_call(
        DOMAIN,
        "log_bottle",
        {"device_id": device.id, "amount": 120.0, "bottle_type": "formula"},
        blocking=True,
    )

    start_time = mock_huckleberry_api.log_bottle.call_args.kwargs["start_time"]
    assert start_time.tzinfo is not None
    assert abs((start_time - datetime.now(timezone.utc)).total_seconds()) < 60


async def test_invalid_datetime_string_is_rejected(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """An unparseable value fails schema validation before reaching the API."""
    device = await _setup(hass, mock_huckleberry_api)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "start_sleep",
            {"device_id": device.id, "start_time": "not a datetime"},
            blocking=True,
        )

    mock_huckleberry_api.start_sleep.assert_not_called()


@pytest.mark.parametrize(
    ("service", "data", "method"),
    [
        ("start_sleep", {"start_time": "2026-09-19 07:30:00"}, "start_sleep"),
        ("complete_sleep", {"end_time": "2026-09-19 08:45:00"}, "complete_sleep"),
        ("set_sleep_start_time", {"start_time": "2026-09-19 07:05:00"}, "set_sleep_start_time"),
    ],
)
async def test_library_value_error_becomes_service_validation_error(
    hass: HomeAssistant, mock_huckleberry_api, service: str, data: dict[str, str], method: str
) -> None:
    """A rejection from huckleberry-api surfaces as a Home Assistant validation error."""
    device = await _setup(hass, mock_huckleberry_api)
    getattr(mock_huckleberry_api, method).side_effect = ValueError("end_time must be after the sleep start time")

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(DOMAIN, service, {"device_id": device.id, **data}, blocking=True)

    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key in ("invalid_start_time", "invalid_end_time")
    # The library's reason is carried through to the user-facing message.
    assert exc_info.value.translation_placeholders == {"error": "end_time must be after the sleep start time"}


async def test_no_active_sleep_surfaces_as_validation_error(hass: HomeAssistant, mock_huckleberry_api) -> None:
    """Adjusting a timer that is not running reports the library's reason."""
    device = await _setup(hass, mock_huckleberry_api)
    mock_huckleberry_api.set_sleep_start_time.side_effect = ValueError("no active sleep")

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "set_sleep_start_time",
            {"device_id": device.id, "start_time": "2026-09-19 07:05:00"},
            blocking=True,
        )

    assert exc_info.value.translation_placeholders == {"error": "no active sleep"}


def test_services_yaml_declares_the_new_fields() -> None:
    """services.yaml is what the UI and YAML automations are written against."""
    import pathlib

    import yaml

    services = yaml.safe_load(
        pathlib.Path("custom_components/huckleberry/services.yaml").read_text(encoding="utf-8")
    )

    assert services["start_sleep"]["fields"]["start_time"]["required"] is False
    assert "datetime" in services["start_sleep"]["fields"]["start_time"]["selector"]

    assert services["complete_sleep"]["fields"]["end_time"]["required"] is False
    assert "datetime" in services["complete_sleep"]["fields"]["end_time"]["selector"]

    assert services["log_bottle"]["fields"]["start_time"]["required"] is False
    assert "datetime" in services["log_bottle"]["fields"]["start_time"]["selector"]

    set_start = services["set_sleep_start_time"]["fields"]
    assert set_start["device_id"]["required"] is True
    assert set_start["start_time"]["required"] is True
    assert "datetime" in set_start["start_time"]["selector"]

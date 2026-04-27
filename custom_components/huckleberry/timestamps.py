"""Timestamp helpers for Huckleberry entities."""
from __future__ import annotations

from datetime import datetime, timezone


def _normalize_unix_timestamp(value: int | float) -> float:
    """Return a unix timestamp in seconds.

    Firebase payloads in this integration mix seconds-based and milliseconds-based
    numeric timestamps. Values larger than 10^11 are treated as milliseconds.
    """
    timestamp = float(value)
    if abs(timestamp) >= 100_000_000_000:
        return timestamp / 1000
    return timestamp


def as_datetime(value: int | float | None) -> datetime | None:
    """Convert a unix timestamp to a UTC datetime."""
    if value is None:
        return None
    return datetime.fromtimestamp(_normalize_unix_timestamp(value), tz=timezone.utc)


def as_iso8601_datetime(value: int | float | None) -> str | None:
    """Convert a unix timestamp to an ISO 8601 string in UTC."""
    date_value = as_datetime(value)
    if date_value is None:
        return None
    return date_value.isoformat()


def as_iso8601_duration(value: int | float | None) -> str | None:
    """Convert a duration in seconds to an ISO 8601 duration string (e.g. ``P1DT2H3M4S``)."""
    if value is None:
        return None

    total_seconds = int(float(value))
    sign = "-" if total_seconds < 0 else ""
    remaining_seconds = abs(total_seconds)

    days, remaining_seconds = divmod(remaining_seconds, 86_400)
    hours, remaining_seconds = divmod(remaining_seconds, 3_600)
    minutes, seconds = divmod(remaining_seconds, 60)

    duration = f"{sign}P"
    if days:
        duration += f"{days}D"

    if hours or minutes or seconds or total_seconds == 0:
        duration += "T"
        if hours:
            duration += f"{hours}H"
        if minutes:
            duration += f"{minutes}M"
        if seconds or total_seconds == 0:
            duration += f"{seconds}S"

    return duration

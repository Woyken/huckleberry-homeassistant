"""Tests for Huckleberry timestamp helpers."""

from custom_components.huckleberry.timestamps import as_iso8601_duration


def test_as_iso8601_duration_returns_none_for_none() -> None:
    """None input should stay None."""
    assert as_iso8601_duration(None) is None


def test_as_iso8601_duration_formats_zero_seconds() -> None:
    """Zero duration should remain explicit."""
    assert as_iso8601_duration(0) == "PT0S"


def test_as_iso8601_duration_formats_time_only_values() -> None:
    """Sub-day durations should use time components only."""
    assert as_iso8601_duration(59) == "PT59S"
    assert as_iso8601_duration(3_600) == "PT1H"
    assert as_iso8601_duration(3_661) == "PT1H1M1S"


def test_as_iso8601_duration_formats_day_values_without_month_rollover() -> None:
    """Large durations should accumulate in days rather than months."""
    assert as_iso8601_duration(86_400) == "P1D"
    assert as_iso8601_duration((123 * 86_400) + 3_600) == "P123DT1H"
    assert as_iso8601_duration((123 * 86_400) + 3_661) == "P123DT1H1M1S"

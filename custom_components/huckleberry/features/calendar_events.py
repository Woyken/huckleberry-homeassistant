"""Calendar event builders for Huckleberry history collections."""
from __future__ import annotations

from datetime import datetime
from typing import Final

from homeassistant.components.calendar import CalendarEvent
from homeassistant.util import dt as dt_util

from huckleberry_api.firebase_types import (
    ActivityMode,
    FirebaseActivityIntervalData,
    FirebaseBottleFeedIntervalData,
    FirebaseBreastFeedIntervalData,
    FirebaseDiaperData,
    FirebaseGrowthData,
    FirebaseMedicationData,
    FirebasePumpIntervalData,
    FirebaseSleepCondition,
    FirebaseSleepDetails,
    FirebaseSleepIntervalData,
    FirebaseSleepLocations,
    FirebaseSolidsFeedIntervalData,
    FirebaseTemperatureData,
    HealthDataEntry,
)

DIAPER_EMOJI: Final[dict[str, str]] = {
    "pee": "💧",
    "poo": "💩",
    "both": "💧💩",
    "dry": "✅",
}
POTTY_RESULT_LABELS: Final[dict[str, str]] = {
    "wentPotty": "Went potty",
    "accident": "Accident",
    "satButDry": "Sat but dry",
}
MEASUREMENT_UNIT_LABELS: Final[dict[str, str]] = {
    "lbs.oz": "lb",
    "ft.in": "ft",
    "hcm": "cm",
    "hin": "in",
    "C": "°C",
    "F": "°F",
}
ACTIVITY_LABELS: Final[dict[ActivityMode, str]] = {
    "bath": "Bath",
    "brushTeeth": "Brush Teeth",
    "indoorPlay": "Indoor Play",
    "outdoorPlay": "Outdoor Play",
    "screenTime": "Screen Time",
    "skinToSkin": "Skin to Skin",
    "storyTime": "Story Time",
    "tummyTime": "Tummy Time",
}
ACTIVITY_EMOJI: Final[dict[ActivityMode, str]] = {
    "bath": "🛁",
    "brushTeeth": "🪥",
    "indoorPlay": "🧩",
    "outdoorPlay": "🌳",
    "screenTime": "📱",
    "skinToSkin": "🤱",
    "storyTime": "📖",
    "tummyTime": "🧸",
}


def build_sleep_events(
    intervals: list[FirebaseSleepIntervalData],
) -> list[CalendarEvent]:
    """Build calendar events from sleep intervals."""
    events: list[CalendarEvent] = []
    for interval in intervals:
        start_time = _event_time(interval.start)
        duration_seconds = float(interval.duration)
        end_time = _event_time(interval.start + duration_seconds)
        duration_str = _format_compact_duration(duration_seconds)

        description_lines = [f"Sleep duration: {_format_duration(duration_seconds)}"]
        _append_sleep_details(description_lines, interval.details)

        events.append(
            CalendarEvent(
                start=start_time,
                end=end_time,
                summary=f"💤 Sleep ({duration_str})",
                description="\n".join(description_lines),
            )
        )
    return events


def build_feed_events(
    intervals: list[
        FirebaseBreastFeedIntervalData
        | FirebaseBottleFeedIntervalData
        | FirebaseSolidsFeedIntervalData
    ],
) -> tuple[list[CalendarEvent], list[CalendarEvent]]:
    """Build calendar events from feed intervals."""
    feed_events: list[CalendarEvent] = []
    bottle_events: list[CalendarEvent] = []

    for interval in intervals:
        start_time = _event_time(interval.start)

        if isinstance(interval, FirebaseBottleFeedIntervalData):
            amount = interval.amount
            units = interval.units
            bottle_type = interval.bottleType

            summary = "🍼 Bottle"
            description = "Bottle feeding"
            if amount is not None:
                summary += f" ({_format_number(amount)} {units})"
                description += f": {_format_number(amount)} {units}"
            if bottle_type:
                description += f"\nType: {bottle_type}"
            if interval.notes:
                description += f"\nNotes: {interval.notes}"

            bottle_events.append(
                CalendarEvent(
                    start=start_time,
                    end=start_time,
                    summary=summary,
                    description=description,
                )
            )
            continue

        if isinstance(interval, FirebaseBreastFeedIntervalData):
            left_duration_seconds = float(interval.leftDuration or 0)
            right_duration_seconds = float(interval.rightDuration or 0)

            total_duration_seconds = int(
                round(left_duration_seconds + right_duration_seconds)
            )
            end_time = _event_time(interval.start + total_duration_seconds)

            left_minutes = int(round(left_duration_seconds / 60))
            right_minutes = int(round(right_duration_seconds / 60))

            sides: list[str] = []
            if left_minutes > 0:
                sides.append(f"L:{left_minutes}m")
            if right_minutes > 0:
                sides.append(f"R:{right_minutes}m")

            sides_str = (
                " ".join(sides)
                if sides
                else _format_duration(total_duration_seconds)
            )
            summary = f"🍼 Feed ({sides_str})"
            description = f"Feeding - Total: {_format_duration(total_duration_seconds)}"
            if left_duration_seconds > 0:
                description += f"\nLeft: {_format_duration(left_duration_seconds)}"
            if right_duration_seconds > 0:
                description += f"\nRight: {_format_duration(right_duration_seconds)}"
            if interval.notes:
                description += f"\nNotes: {interval.notes}"

            feed_events.append(
                CalendarEvent(
                    start=start_time,
                    end=end_time,
                    summary=summary,
                    description=description,
                )
            )
            continue

        # Solids
        food_names = _solids_food_names(interval)
        summary = "🥄 Solids"
        if food_names:
            summary += f" ({', '.join(food_names)})"

        description_lines = ["Solid food feeding"]
        if food_names:
            description_lines.append(f"Foods: {', '.join(food_names)}")

        reactions = [
            reaction
            for reaction, selected in (interval.reactions or {}).items()
            if selected
        ]
        if reactions:
            description_lines.append(f"Reaction: {', '.join(reactions)}")
        if interval.notes:
            description_lines.append(f"Notes: {interval.notes}")

        feed_events.append(
            CalendarEvent(
                start=start_time,
                end=start_time,
                summary=summary,
                description="\n".join(description_lines),
            )
        )

    return feed_events, bottle_events


def build_diaper_events(
    intervals: list[FirebaseDiaperData],
) -> list[CalendarEvent]:
    """Build calendar events from diaper and potty intervals."""
    events: list[CalendarEvent] = []
    for interval in intervals:
        event_time = _event_time(interval.start)
        mode = interval.mode
        is_potty = bool(interval.isPotty)
        event_kind = "Potty" if is_potty else "Diaper"
        emoji = "🚽" if is_potty else DIAPER_EMOJI.get(mode, "🩲")

        summary = f"{emoji} {event_kind} ({mode.capitalize()}"
        if is_potty and interval.howItHappened:
            summary += f", {POTTY_RESULT_LABELS.get(interval.howItHappened, interval.howItHappened)}"
        summary += ")"

        description_lines = [f"{event_kind}: {mode}"]
        if is_potty and interval.howItHappened:
            description_lines.append(
                "How it happened: "
                f"{POTTY_RESULT_LABELS.get(interval.howItHappened, interval.howItHappened)}"
            )

        quantity = interval.quantity
        if quantity is not None:
            pee_quantity = _quantity_label(quantity.pee)
            poo_quantity = _quantity_label(quantity.poo)
            if pee_quantity is not None:
                description_lines.append(f"Pee amount: {pee_quantity}")
            if poo_quantity is not None:
                description_lines.append(f"Poo amount: {poo_quantity}")

        if interval.color is not None:
            description_lines.append(f"Color: {interval.color}")
        if interval.consistency is not None:
            description_lines.append(f"Consistency: {interval.consistency}")
        if interval.diaperRash:
            description_lines.append("Diaper rash: yes")
        if interval.notes:
            description_lines.append(f"Notes: {interval.notes}")

        events.append(
            CalendarEvent(
                start=event_time,
                end=event_time,
                summary=summary,
                description="\n".join(description_lines),
            )
        )
    return events


def build_health_events(entries: list[HealthDataEntry]) -> list[CalendarEvent]:
    """Build calendar events from health entries."""
    events: list[CalendarEvent] = []
    for entry in entries:
        event_time = _event_time(entry.start)

        if isinstance(entry, FirebaseGrowthData):
            description_lines = ["Growth measurement"]
            if entry.weight is not None:
                description_lines.append(
                    f"Weight: {_format_measurement(entry.weight, entry.weightUnits)}"
                )
            if entry.height is not None:
                description_lines.append(
                    f"Height: {_format_measurement(entry.height, entry.heightUnits)}"
                )
            if entry.head is not None:
                description_lines.append(
                    f"Head: {_format_measurement(entry.head, entry.headUnits)}"
                )
            summary = "📏 Growth Measurement"
        elif isinstance(entry, FirebaseMedicationData):
            summary = f"💊 Medication ({entry.medication_name})"
            description_lines = [f"Medication: {entry.medication_name}"]
            if entry.amount is not None and (
                entry.amount != 0 or entry.units is not None
            ):
                description_lines.append(
                    f"Amount: {_format_measurement(entry.amount, entry.units)}"
                )
            if entry.notes:
                description_lines.append(f"Notes: {entry.notes}")
        elif isinstance(entry, FirebaseTemperatureData):
            summary = "🌡️ Temperature"
            description_lines = [
                f"Temperature: {_format_measurement(entry.amount, entry.units)}"
            ]
            if entry.notes:
                description_lines.append(f"Notes: {entry.notes}")
        else:
            continue

        events.append(
            CalendarEvent(
                start=event_time,
                end=event_time,
                summary=summary,
                description="\n".join(description_lines),
            )
        )
    return events


def build_pump_events(
    intervals: list[FirebasePumpIntervalData],
) -> list[CalendarEvent]:
    """Build calendar events from pump intervals."""
    events: list[CalendarEvent] = []
    for interval in intervals:
        start_time = _event_time(interval.start)
        duration_seconds = float(interval.duration or 0)
        end_time = (
            _event_time(interval.start + duration_seconds)
            if duration_seconds > 0
            else start_time
        )

        total_amount = _pump_total(interval)
        summary_parts: list[str] = []
        if duration_seconds > 0:
            summary_parts.append(_format_compact_duration(duration_seconds))
        if total_amount is not None:
            summary_parts.append(f"{_format_number(total_amount)} {interval.units}")
        summary = "🍼 Pump"
        if summary_parts:
            summary += f" ({' · '.join(summary_parts)})"

        description_lines = ["Pumping session"]
        if interval.entryMode == "total" and total_amount is not None:
            description_lines.append(
                f"Total: {_format_number(total_amount)} {interval.units}"
            )
        else:
            if interval.leftAmount is not None:
                description_lines.append(
                    f"Left: {_format_number(interval.leftAmount)} {interval.units}"
                )
            if interval.rightAmount is not None:
                description_lines.append(
                    f"Right: {_format_number(interval.rightAmount)} {interval.units}"
                )
            if total_amount is not None:
                description_lines.append(
                    f"Total: {_format_number(total_amount)} {interval.units}"
                )
        if duration_seconds > 0:
            description_lines.append(
                f"Duration: {_format_duration(duration_seconds)}"
            )
        if interval.notes:
            description_lines.append(f"Notes: {interval.notes}")

        events.append(
            CalendarEvent(
                start=start_time,
                end=end_time,
                summary=summary,
                description="\n".join(description_lines),
            )
        )
    return events


def build_activity_events(
    intervals: list[FirebaseActivityIntervalData],
) -> list[CalendarEvent]:
    """Build calendar events from activity intervals."""
    events: list[CalendarEvent] = []
    for interval in intervals:
        start_time = _event_time(interval.start)
        duration_seconds = float(interval.duration or 0)
        end_time = (
            _event_time(interval.start + duration_seconds)
            if duration_seconds > 0
            else start_time
        )

        label = ACTIVITY_LABELS.get(interval.mode, interval.mode)
        summary = f"{ACTIVITY_EMOJI.get(interval.mode, '🧸')} {label}"
        description_lines = [f"Activity: {label}"]
        if duration_seconds > 0:
            summary += f" ({_format_compact_duration(duration_seconds)})"
            description_lines.append(
                f"Duration: {_format_duration(duration_seconds)}"
            )
        if interval.notes:
            description_lines.append(f"Notes: {interval.notes}")

        events.append(
            CalendarEvent(
                start=start_time,
                end=end_time,
                summary=summary,
                description="\n".join(description_lines),
            )
        )
    return events


def _event_time(timestamp: int | float) -> datetime:
    """Return an event timestamp in the configured time zone."""
    return datetime.fromtimestamp(timestamp, tz=dt_util.DEFAULT_TIME_ZONE)


def _format_duration(duration_seconds: float | int) -> str:
    """Format duration in seconds as readable min/sec text."""
    total_seconds = int(round(float(duration_seconds)))
    minutes, seconds = divmod(total_seconds, 60)

    if minutes > 0 and seconds > 0:
        return f"{minutes} min {seconds} sec"
    if minutes > 0:
        return f"{minutes} min"
    return f"{seconds} sec"


def _format_compact_duration(duration_seconds: float | int) -> str:
    """Format duration in seconds using compact hour/minute text."""
    total_seconds = int(round(float(duration_seconds)))
    hours, remaining_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remaining_seconds, 60)

    if hours > 0:
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    if minutes > 0:
        return f"{minutes}m"
    return f"{seconds}s"


def _format_number(value: int | float) -> str:
    """Format a numeric amount without a redundant decimal part."""
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)


def _format_measurement(value: int | float, units: str | None) -> str:
    """Format a measurement with its unit when available."""
    formatted_value = _format_number(value)
    if units is None:
        return formatted_value
    return f"{formatted_value} {MEASUREMENT_UNIT_LABELS.get(units, units)}"


def _quantity_label(value: int | float | None) -> str | None:
    """Return the app's diaper quantity label for a stored quantity value."""
    if value is None:
        return None

    return {
        0.0: "little",
        50.0: "medium",
        100.0: "big",
    }.get(float(value), _format_number(value))


def _solids_food_names(interval: FirebaseSolidsFeedIntervalData) -> list[str]:
    """Return solid food names with any recorded amount."""
    if not interval.foods:
        return []

    names: list[str] = []
    for food in interval.foods.values():
        name = food.created_name
        if food.amount not in (None, ""):
            name += f" ({food.amount})"
        names.append(name)
    return names


def _append_sleep_details(
    description_lines: list[str],
    details: FirebaseSleepDetails | None,
) -> None:
    """Append the recorded sleep details to an event description."""
    if details is None:
        return

    if details.notes:
        description_lines.append(f"Notes: {details.notes}")

    start_conditions = _sleep_condition_labels(details.startSleepCondition)
    if start_conditions:
        description_lines.append(f"Start condition: {', '.join(start_conditions)}")

    sleep_locations = _sleep_location_labels(details.sleepLocations)
    if sleep_locations:
        description_lines.append(f"Sleep location: {', '.join(sleep_locations)}")

    end_conditions = _sleep_condition_labels(details.endSleepCondition)
    if end_conditions:
        description_lines.append(f"End condition: {', '.join(end_conditions)}")


def _sleep_condition_labels(condition: FirebaseSleepCondition | None) -> list[str]:
    """Return readable labels for recorded sleep conditions."""
    if condition is None:
        return []

    labels: list[str] = []
    if condition.happy:
        labels.append("Happy")
    if condition.longTimeToFallAsleep:
        labels.append("Long time to fall asleep")
    if condition.upset:
        labels.append("Upset")
    if condition.wokeUpChild:
        labels.append("Woke up child")
    if condition.under_10_minutes:
        labels.append("Under 10 minutes")
    if condition.ten_to_twenty_minutes:
        labels.append("10-20 minutes")
    return labels


def _sleep_location_labels(locations: FirebaseSleepLocations | None) -> list[str]:
    """Return readable labels for recorded sleep locations."""
    if locations is None:
        return []

    labels: list[str] = []
    if locations.car:
        labels.append("Car")
    if locations.nursing:
        labels.append("Nursing")
    if locations.wornOrHeld:
        labels.append("Worn or held")
    if locations.stroller:
        labels.append("Stroller")
    if locations.coSleep:
        labels.append("Co-sleep")
    if locations.nextToCarer:
        labels.append("Next to carer")
    if locations.onOwnInBed:
        labels.append("On own in bed")
    if locations.bottle:
        labels.append("Bottle")
    if locations.swing:
        labels.append("Swing")
    return labels


def _pump_total(interval: FirebasePumpIntervalData) -> float | None:
    """Return the total pumped amount when both sides are recorded."""
    if interval.leftAmount is None or interval.rightAmount is None:
        return None
    return float(interval.leftAmount) + float(interval.rightAmount)

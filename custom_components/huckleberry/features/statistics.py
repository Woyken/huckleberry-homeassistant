"""Daily statistics sensors for Huckleberry."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import DailyStatistics, HuckleberryChildProfile


def build_statistics_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build daily statistics sensors for each child."""
    entities: list[SensorEntity] = []
    for child in children:
        entities.append(DiapersTodaySensor(coordinator, child))
        entities.append(BottlesTodaySensor(coordinator, child))
        entities.append(NursingTodaySensor(coordinator, child))
        entities.append(SleepTodaySensor(coordinator, child))
    return entities


def _format_duration(total_seconds: int) -> str:
    """Format seconds as 'Xh Ym' for display."""
    if total_seconds <= 0:
        return "0m"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h"
    return f"{minutes}m"


class _DailyStatisticsSensorBase(HuckleberryBaseEntity, SensorEntity):
    """Base class for daily statistics sensors."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def _get_stats(self) -> DailyStatistics | None:
        return self.coordinator.get_daily_statistics(self.child_uid)


class DiapersTodaySensor(_DailyStatisticsSensorBase):
    """Sensor showing today's total diaper changes."""

    _attr_icon = "mdi:baby"
    _attr_translation_key = "diapers_today"
    _attr_native_unit_of_measurement = "changes"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_diapers_today"

    @property
    def native_value(self) -> int | None:
        stats = self._get_stats()
        return stats.diaper_count if stats is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        stats = self._get_stats()
        if stats is None:
            return {}
        return {
            "pee_only": stats.diaper_pee_count,
            "poo_only": stats.diaper_poo_count,
            "mixed": stats.diaper_mixed_count,
            "date": stats.date,
        }


class BottlesTodaySensor(_DailyStatisticsSensorBase):
    """Sensor showing today's total bottle feedings."""

    _attr_icon = "mdi:baby-bottle"
    _attr_translation_key = "bottles_today"
    _attr_native_unit_of_measurement = "bottles"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_bottles_today"

    @property
    def native_value(self) -> int | None:
        stats = self._get_stats()
        return stats.bottle_count if stats is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        stats = self._get_stats()
        if stats is None:
            return {}
        return {
            "total_ml": round(stats.bottle_total_ml, 1),
            "date": stats.date,
        }


class NursingTodaySensor(_DailyStatisticsSensorBase):
    """Sensor showing today's total nursing sessions."""

    _attr_icon = "mdi:mother-nurse"
    _attr_translation_key = "nursing_today"
    _attr_native_unit_of_measurement = "sessions"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_nursing_today"

    @property
    def native_value(self) -> int | None:
        stats = self._get_stats()
        return stats.nursing_count if stats is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        stats = self._get_stats()
        if stats is None:
            return {}
        return {
            "total_duration": _format_duration(stats.nursing_total_seconds),
            "total_minutes": stats.nursing_total_seconds // 60,
            "date": stats.date,
        }


class SleepTodaySensor(_DailyStatisticsSensorBase):
    """Sensor showing today's total sleep."""

    _attr_icon = "mdi:sleep"
    _attr_translation_key = "sleep_today"
    _attr_native_unit_of_measurement = "sessions"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        child: HuckleberryChildProfile,
    ) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_sleep_today"

    @property
    def native_value(self) -> int | None:
        stats = self._get_stats()
        return stats.sleep_count if stats is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        stats = self._get_stats()
        if stats is None:
            return {}
        return {
            "total_duration": _format_duration(stats.sleep_total_seconds),
            "total_minutes": stats.sleep_total_seconds // 60,
            "date": stats.date,
        }

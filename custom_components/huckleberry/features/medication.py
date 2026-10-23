"""Medication-related sensors for Huckleberry."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from huckleberry_api.firebase_types import FirebaseLastMedicationData

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_datetime, as_iso8601_datetime


def build_medication_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build medication sensors."""
    return [HuckleberryMedicationSensor(coordinator, child) for child in children]


class HuckleberryMedicationSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing the latest medication dose."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:pill"
    _attr_translation_key = "medication"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_medication"

    def _last_medication(self) -> FirebaseLastMedicationData | None:
        state = self.coordinator.get_state(self.child_uid)
        return state.medication_data if state is not None else None

    @property
    def native_value(self):
        """Return the latest medication timestamp."""
        medication = self._last_medication()
        return as_datetime(medication.start if medication is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return latest medication details."""
        medication = self._last_medication()
        if medication is None:
            return {}

        attributes: dict[str, object] = {"time": as_iso8601_datetime(medication.start)}
        if medication.medication_id is not None:
            attributes["medication_id"] = medication.medication_id
        if medication.medication_name is not None:
            attributes["medication_name"] = medication.medication_name
        if medication.amount is not None:
            attributes["amount"] = medication.amount
        if medication.units is not None:
            attributes["units"] = medication.units
        if medication.notes:
            attributes["notes"] = medication.notes

        return attributes

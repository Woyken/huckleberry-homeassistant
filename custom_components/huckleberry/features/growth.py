"""Growth-related sensors for Huckleberry."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile
from ..timestamps import as_datetime


def build_growth_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build growth sensors."""
    return [HuckleberryGrowthSensor(coordinator, child) for child in children]


class HuckleberryGrowthSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing child growth measurements."""

    _attr_icon = "mdi:human-male-height"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_name = "Growth"
        self._attr_unique_id = f"{self.child_uid}_growth"

    @property
    def native_value(self):
        """Return the most recent measurement timestamp."""
        state = self.coordinator.get_state(self.child_uid)
        growth_data = state.growth_data if state is not None else None

        return as_datetime(growth_data.start if growth_data is not None else None)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return growth measurement attributes."""
        state = self.coordinator.get_state(self.child_uid)
        growth_data = state.growth_data if state is not None else None
        if growth_data is None:
            return {}

        attributes: dict[str, object] = {}
        if growth_data.weight is not None:
            attributes["weight"] = growth_data.weight
            attributes["weight_unit"] = growth_data.weightUnits
        if growth_data.height is not None:
            attributes["height"] = growth_data.height
            attributes["height_unit"] = growth_data.heightUnits
        if growth_data.head is not None:
            attributes["head_circumference"] = growth_data.head
            attributes["head_unit"] = growth_data.headUnits

        return attributes

"""Child-related sensors for Huckleberry."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .. import HuckleberryDataUpdateCoordinator
from ..entity import HuckleberryBaseEntity
from ..models import HuckleberryChildProfile, children_sensor_attributes


def build_child_sensors(
    coordinator: HuckleberryDataUpdateCoordinator,
    children: list[HuckleberryChildProfile],
) -> list[SensorEntity]:
    """Build child profile sensors."""
    entities: list[SensorEntity] = [HuckleberryChildrenSensor(coordinator, children)]
    for child in children:
        entities.append(HuckleberryChildProfileSensor(coordinator, child))
    return entities


class HuckleberryChildrenSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing children information."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:account-child"
    _attr_translation_key = "children"

    def __init__(
        self,
        coordinator: HuckleberryDataUpdateCoordinator,
        children: list[HuckleberryChildProfile],
    ) -> None:
        super().__init__(coordinator)
        self._children = children
        self._attr_unique_id = "huckleberry_children"

    @property
    def native_value(self):
        """Return the count of children."""
        return len(self._children)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes."""
        return children_sensor_attributes(self._children)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success


class HuckleberryChildProfileSensor(HuckleberryBaseEntity, SensorEntity):
    """Sensor showing individual child profile information."""

    _attr_icon = "mdi:account"
    _attr_translation_key = "profile"

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
        super().__init__(coordinator, child)
        self._attr_unique_id = f"{self.child_uid}_profile"

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use in the frontend."""
        return self._child.picture

    @property
    def native_value(self):
        """Return the child's name as the state."""
        return self.child_name

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return child profile attributes."""
        return self._child.as_attributes()

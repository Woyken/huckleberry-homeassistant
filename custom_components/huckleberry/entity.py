"""Base entity for Huckleberry."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .models import HuckleberryChildProfile


class HuckleberryBaseEntity(CoordinatorEntity):
    """Base entity for Huckleberry."""

    def __init__(self, coordinator: CoordinatorEntity, child: HuckleberryChildProfile) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._child = child
        self.child_uid = child.uid
        self.child_name = child.name
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        device_info = DeviceInfo(
            identifiers={(DOMAIN, self.child_uid)},
            name=self.child_name,
            manufacturer="Huckleberry",
        )
        if self._child.picture is not None:
            device_info["configuration_url"] = self._child.picture
        return device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.child_uid in self.coordinator.data
"""Base entity for Huckleberry."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class HuckleberryBaseEntity(CoordinatorEntity):
    """Base entity for Huckleberry."""

    def __init__(self, coordinator, child: dict[str, Any]) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._child = child
        self.child_uid = child["uid"]
        self.child_name = child["name"]
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        device_info = {
            "identifiers": {(DOMAIN, self.child_uid)},
            "name": self.child_name,
            "manufacturer": "Huckleberry",
        }
        # Add profile picture as configuration_url if available
        if self._child.get("picture"):
            device_info["configuration_url"] = self._child["picture"]
        return device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.child_uid in self.coordinator.data
        )

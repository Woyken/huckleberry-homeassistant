"""Base entity for Huckleberry."""
from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .models import HuckleberryChildProfile

if TYPE_CHECKING:
    from . import HuckleberryDataUpdateCoordinator


def _valid_configuration_url(value: str | None) -> str | None:
    """Return a valid Home Assistant configuration URL or None."""
    if value is None:
        return None

    normalized_value = value.strip()
    if not normalized_value:
        return None

    parsed_value = urlparse(normalized_value)
    if parsed_value.scheme not in {"http", "https"} or not parsed_value.netloc:
        return None

    return normalized_value


class HuckleberryBaseEntity(CoordinatorEntity["HuckleberryDataUpdateCoordinator"]):
    """Base entity for Huckleberry."""

    def __init__(self, coordinator: HuckleberryDataUpdateCoordinator, child: HuckleberryChildProfile) -> None:
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
        configuration_url = _valid_configuration_url(self._child.picture)
        if configuration_url is not None:
            device_info["configuration_url"] = configuration_url
        return device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.child_uid in self.coordinator.data

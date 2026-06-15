"""Shared entities for SIP Indoor Station."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME, DOMAIN
from .coordinator import SipIndoorStationCoordinator


class SipIndoorStationEntity(CoordinatorEntity[SipIndoorStationCoordinator]):
    """Base SIP Indoor Station entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SipIndoorStationCoordinator,
        key: str,
        translation_key: str,
        name: str,
    ) -> None:
        """Initialize entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_translation_key = translation_key
        device_name = coordinator.entry.data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
        sw_version = self.state_data.get("version")
        if not isinstance(sw_version, str):
            sw_version = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=device_name,
            manufacturer="AZX",
            model="SIP Indoor Station",
            sw_version=sw_version,
        )

    @property
    def state_data(self) -> dict[str, Any]:
        """Return latest state payload."""
        return self.coordinator.data or {}

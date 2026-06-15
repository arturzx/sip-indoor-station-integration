"""Binary sensors for SIP Indoor Station."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import SipIndoorStationCoordinator
from .entity import SipIndoorStationEntity


@dataclass(frozen=True, kw_only=True)
class SipBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor description."""

    field: str
    display_name: str


DESCRIPTIONS = (
    SipBinarySensorDescription(
        key="registered",
        translation_key="registered",
        field="registered",
        display_name="Registered",
    ),
    SipBinarySensorDescription(
        key="ringing",
        translation_key="ringing",
        field="ringing",
        display_name="Ringing",
    ),
    SipBinarySensorDescription(
        key="in_call",
        translation_key="in_call",
        field="in_call",
        display_name="In call",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: SipIndoorStationCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(SipIndoorStationBinarySensor(coordinator, description) for description in DESCRIPTIONS)


class SipIndoorStationBinarySensor(SipIndoorStationEntity, BinarySensorEntity):
    """SIP Indoor Station binary sensor."""

    entity_description: SipBinarySensorDescription

    def __init__(
        self,
        coordinator: SipIndoorStationCoordinator,
        description: SipBinarySensorDescription,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(
            coordinator,
            description.key,
            description.translation_key or description.key,
            description.display_name,
        )
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return current binary state."""
        value: Any = self.state_data.get(self.entity_description.field)
        return bool(value) if value is not None else None

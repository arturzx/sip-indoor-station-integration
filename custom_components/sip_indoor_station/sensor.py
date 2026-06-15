"""Sensors for SIP Indoor Station."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import SipIndoorStationCoordinator
from .entity import SipIndoorStationEntity


DESCRIPTION = SensorEntityDescription(key="call_state", translation_key="call_state")
DISPLAY_NAME = "Call state"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: SipIndoorStationCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([SipIndoorStationCallStateSensor(coordinator)])


class SipIndoorStationCallStateSensor(SipIndoorStationEntity, SensorEntity):
    """Call state sensor."""

    entity_description = DESCRIPTION

    def __init__(self, coordinator: SipIndoorStationCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(
            coordinator,
            DESCRIPTION.key,
            DESCRIPTION.translation_key or DESCRIPTION.key,
            DISPLAY_NAME,
        )

    @property
    def native_value(self) -> str | None:
        """Return call state."""
        value = self.state_data.get("call_state")
        return str(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object | None]:
        """Return useful call attributes."""
        data = self.state_data
        return {
            "call_id": data.get("call_id"),
            "remote_ip": data.get("remote_ip"),
            "registration_user": data.get("registration_user"),
            "registration_source": data.get("registration_source"),
            "selected_audio_codec": data.get("selected_audio_codec"),
            "selected_audio_payload_type": data.get("selected_audio_payload_type"),
            "last_event": data.get("last_event"),
            "last_event_at": data.get("last_event_at"),
        }

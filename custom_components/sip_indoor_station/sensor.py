"""Sensors for SIP Indoor Station."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DATA_HISTORY_COORDINATOR, DOMAIN
from .coordinator import SipIndoorStationCoordinator, SipIndoorStationHistoryCoordinator
from .entity import SipIndoorStationEntity


DESCRIPTION = SensorEntityDescription(key="call_state", translation_key="call_state")
DISPLAY_NAME = "Call state"
LAST_CALL_DESCRIPTION = SensorEntityDescription(
    key="last_call",
    translation_key="last_call",
    device_class=SensorDeviceClass.TIMESTAMP,
)
LAST_MISSED_CALL_DESCRIPTION = SensorEntityDescription(
    key="last_missed_call",
    translation_key="last_missed_call",
    device_class=SensorDeviceClass.TIMESTAMP,
)
MISSED_CALL_COUNT_DESCRIPTION = SensorEntityDescription(
    key="missed_call_count",
    translation_key="missed_call_count",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: SipIndoorStationCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    history_coordinator: SipIndoorStationHistoryCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_HISTORY_COORDINATOR
    ]
    async_add_entities(
        [
            SipIndoorStationCallStateSensor(coordinator),
            SipIndoorStationLastCallSensor(history_coordinator),
            SipIndoorStationLastMissedCallSensor(history_coordinator),
            SipIndoorStationMissedCallCountSensor(history_coordinator),
        ]
    )


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


class SipIndoorStationHistorySensor(SipIndoorStationEntity, SensorEntity):
    """Base call history summary sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: SipIndoorStationHistoryCoordinator,
        description: SensorEntityDescription,
        name: str,
    ) -> None:
        """Initialize sensor."""
        super().__init__(
            coordinator,
            description.key,
            description.translation_key or description.key,
            name,
        )
        self.entity_description = description

    @property
    def calls(self) -> list[dict[str, Any]]:
        """Return history call records."""
        calls = self.state_data.get("calls")
        if not isinstance(calls, list):
            return []
        return [call for call in calls if isinstance(call, dict)]

    @property
    def call(self) -> dict[str, Any] | None:
        """Return selected history call."""
        raise NotImplementedError

    @property
    def native_value(self) -> datetime | None:
        """Return selected call timestamp."""
        call = self.call
        if call is None:
            return None
        return parse_timestamp(call.get("started_at"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return selected call details."""
        call = self.call
        if call is None:
            return {}
        attributes = dict(call)
        history_id = attributes.get("id")
        if attributes.get("has_snapshot") and isinstance(history_id, str):
            attributes["snapshot_url"] = f"/api/sip_indoor_station/call_history/{history_id}/snapshot"
        return attributes


class SipIndoorStationLastCallSensor(SipIndoorStationHistorySensor):
    """Last call history sensor."""

    def __init__(self, coordinator: SipIndoorStationHistoryCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, LAST_CALL_DESCRIPTION, "Last call")

    @property
    def call(self) -> dict[str, Any] | None:
        """Return most recent call."""
        return self.calls[0] if self.calls else None


class SipIndoorStationLastMissedCallSensor(SipIndoorStationHistorySensor):
    """Last missed call history sensor."""

    def __init__(self, coordinator: SipIndoorStationHistoryCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, LAST_MISSED_CALL_DESCRIPTION, "Last missed call")

    @property
    def call(self) -> dict[str, Any] | None:
        """Return most recent missed call."""
        return next((call for call in self.calls if call.get("status") == "missed"), None)


class SipIndoorStationMissedCallCountSensor(SipIndoorStationEntity, SensorEntity):
    """Missed call count sensor."""

    entity_description = MISSED_CALL_COUNT_DESCRIPTION

    def __init__(self, coordinator: SipIndoorStationHistoryCoordinator) -> None:
        """Initialize sensor."""
        super().__init__(
            coordinator,
            MISSED_CALL_COUNT_DESCRIPTION.key,
            MISSED_CALL_COUNT_DESCRIPTION.translation_key or MISSED_CALL_COUNT_DESCRIPTION.key,
            "Missed call count",
        )

    @property
    def native_value(self) -> int:
        """Return number of missed calls in loaded history."""
        return len([call for call in self.calls if call.get("status") == "missed"])

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Return count context."""
        return {"total_loaded_calls": len(self.calls)}

    @property
    def calls(self) -> list[dict[str, Any]]:
        """Return history call records."""
        calls = self.state_data.get("calls")
        if not isinstance(calls, list):
            return []
        return [call for call in calls if isinstance(call, dict)]


def parse_timestamp(value: object) -> datetime | None:
    """Parse add-on ISO timestamp."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

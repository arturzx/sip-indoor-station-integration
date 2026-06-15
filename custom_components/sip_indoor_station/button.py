"""Buttons for SIP Indoor Station."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import SipIndoorStationCoordinator
from .entity import SipIndoorStationEntity


@dataclass(frozen=True, kw_only=True)
class SipButtonDescription(ButtonEntityDescription):
    """Button description."""

    command: str
    display_name: str


DESCRIPTIONS = (
    SipButtonDescription(key="answer", translation_key="answer", command="answer", display_name="Answer"),
    SipButtonDescription(key="reject", translation_key="reject", command="reject", display_name="Reject"),
    SipButtonDescription(key="hang_up", translation_key="hang_up", command="hangup", display_name="Hang up"),
    SipButtonDescription(key="open_door", translation_key="open_door", command="open_door", display_name="Open door"),
    SipButtonDescription(key="reboot", translation_key="reboot", command="reboot", display_name="Reboot"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons."""
    coordinator: SipIndoorStationCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(SipIndoorStationButton(coordinator, description) for description in DESCRIPTIONS)


class SipIndoorStationButton(SipIndoorStationEntity, ButtonEntity):
    """Command button."""

    entity_description: SipButtonDescription

    def __init__(
        self,
        coordinator: SipIndoorStationCoordinator,
        description: SipButtonDescription,
    ) -> None:
        """Initialize button."""
        super().__init__(
            coordinator,
            description.key,
            description.translation_key or description.key,
            description.display_name,
        )
        self.entity_description = description

    async def async_press(self) -> None:
        """Press button."""
        await self.coordinator.async_command(self.entity_description.command)

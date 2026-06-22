"""SIP Indoor Station integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import SipIndoorStationApiClient
from .const import (
    ATTR_HISTORY_ID,
    ATTR_ENTRY_ID,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DATA_HISTORY_COORDINATOR,
    DATA_PROXY,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_CALL_HISTORY,
    SERVICE_DELETE_CALL_HISTORY_ENTRY,
    SERVICE_REFRESH_CALL_HISTORY,
)
from .coordinator import SipIndoorStationCoordinator, SipIndoorStationHistoryCoordinator
from .http import SipIndoorStationProxy, register_http_views


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up SIP Indoor Station integration services."""
    hass.data.setdefault(DOMAIN, {})
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SIP Indoor Station from a config entry."""
    _async_register_services(hass)
    client = SipIndoorStationApiClient(hass, entry)
    coordinator = SipIndoorStationCoordinator(hass, entry, client)
    history_coordinator = SipIndoorStationHistoryCoordinator(hass, entry, client)
    history_coordinator.async_set_updated_data({"calls": []})
    await coordinator.async_load_config()
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_start()

    proxy = SipIndoorStationProxy(client, history_coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
        DATA_HISTORY_COORDINATOR: history_coordinator,
        DATA_PROXY: proxy,
    }
    register_http_views(hass, proxy)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload SIP Indoor Station."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if data is not None:
        await data[DATA_COORDINATOR].async_stop()
    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH_CALL_HISTORY):
        return

    async def refresh_call_history(call: ServiceCall) -> None:
        """Refresh call history from the add-on."""
        for coordinator in _history_coordinators_for_call(hass, call):
            await coordinator.async_request_refresh()

    async def delete_call_history_entry(call: ServiceCall) -> None:
        """Delete one call history entry."""
        history_id = call.data[ATTR_HISTORY_ID]
        for coordinator in _history_coordinators_for_call(hass, call):
            await coordinator.async_delete_entry(history_id)

    async def clear_call_history(call: ServiceCall) -> None:
        """Clear call history."""
        for coordinator in _history_coordinators_for_call(hass, call):
            await coordinator.async_clear()

    entry_id_field = vol.Optional(ATTR_ENTRY_ID)
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_CALL_HISTORY,
        refresh_call_history,
        schema=vol.Schema({entry_id_field: cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_CALL_HISTORY_ENTRY,
        delete_call_history_entry,
        schema=vol.Schema({entry_id_field: cv.string, vol.Required(ATTR_HISTORY_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_CALL_HISTORY,
        clear_call_history,
        schema=vol.Schema({entry_id_field: cv.string}),
    )


def _history_coordinators_for_call(
    hass: HomeAssistant,
    call: ServiceCall,
) -> list[SipIndoorStationHistoryCoordinator]:
    """Return targeted history coordinators for a service call."""
    domain_data = hass.data.get(DOMAIN, {})
    entry_id = call.data.get(ATTR_ENTRY_ID)
    if entry_id:
        entry_data = domain_data.get(entry_id)
        if entry_data is None:
            return []
        coordinator = entry_data.get(DATA_HISTORY_COORDINATOR)
        return [coordinator] if coordinator is not None else []
    return [
        entry_data[DATA_HISTORY_COORDINATOR]
        for entry_data in domain_data.values()
        if DATA_HISTORY_COORDINATOR in entry_data
    ]

"""SIP Indoor Station integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import SipIndoorStationApiClient
from .const import DATA_CLIENT, DATA_COORDINATOR, DATA_PROXY, DOMAIN, PLATFORMS
from .coordinator import SipIndoorStationCoordinator
from .http import SipIndoorStationProxy, register_http_views


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SIP Indoor Station from a config entry."""
    client = SipIndoorStationApiClient(hass, entry)
    coordinator = SipIndoorStationCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_start()

    proxy = SipIndoorStationProxy(client)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
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

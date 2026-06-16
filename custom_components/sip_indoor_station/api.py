"""Client for the SIP Indoor Station add-on HTTP API."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_ADDON_SLUG, CONF_ADDON_URL, DEFAULT_ADDON_PORT

LOGGER = logging.getLogger(__name__)


class SipIndoorStationApiError(Exception):
    """Raised when the add-on API request fails."""


class SipIndoorStationApiClient:
    """Async client for the add-on HTTP API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the client."""
        self.hass = hass
        self.entry = entry

    @property
    def session(self) -> aiohttp.ClientSession:
        """Return Home Assistant shared aiohttp session."""
        return async_get_clientsession(self.hass)

    @property
    def addon_base_url(self) -> str:
        """Return add-on upstream base URL."""
        configured_url = self.entry.data.get(CONF_ADDON_URL, "").strip()
        if configured_url:
            return configured_url.rstrip("/")

        slug = self.entry.data[CONF_ADDON_SLUG]
        hostname = slug.replace("_", "-")
        return f"http://{hostname}:{DEFAULT_ADDON_PORT}"

    def http_url(self, path: str) -> str:
        """Return add-on HTTP URL for path."""
        return urljoin(f"{self.addon_base_url}/", path.lstrip("/"))

    def ws_url(self, path: str) -> str:
        """Return add-on WebSocket URL for path."""
        http_url = self.http_url(path)
        if http_url.startswith("https://"):
            return f"wss://{http_url.removeprefix('https://')}"
        return f"ws://{http_url.removeprefix('http://')}"

    async def async_get_state(self) -> dict[str, Any]:
        """Fetch current add-on state."""
        url = self.http_url("/api/state")
        try:
            async with self.session.get(url) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise SipIndoorStationApiError(f"GET /api/state failed: {response.status} {body}")
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise SipIndoorStationApiError(f"GET /api/state failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise SipIndoorStationApiError("GET /api/state returned non-object JSON")
        return payload

    async def async_get_call_history(self, limit: int = 50) -> dict[str, Any]:
        """Fetch recent call history from the add-on."""
        url = self.http_url("/api/call_history")
        try:
            async with self.session.get(url, params={"limit": str(limit)}) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise SipIndoorStationApiError(f"GET /api/call_history failed: {response.status} {body}")
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise SipIndoorStationApiError(f"GET /api/call_history failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise SipIndoorStationApiError("GET /api/call_history returned non-object JSON")
        return payload

    async def async_get_call_history_entry(self, history_id: str) -> dict[str, Any]:
        """Fetch one call history entry from the add-on."""
        url = self.http_url(f"/api/call_history/{history_id}")
        try:
            async with self.session.get(url) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise SipIndoorStationApiError(f"GET /api/call_history/{history_id} failed: {response.status} {body}")
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise SipIndoorStationApiError(f"GET /api/call_history/{history_id} failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise SipIndoorStationApiError("GET /api/call_history/{history_id} returned non-object JSON")
        return payload

    async def async_delete_call_history_entry(self, history_id: str) -> dict[str, Any]:
        """Delete one call history entry from the add-on."""
        url = self.http_url(f"/api/call_history/{history_id}")
        try:
            async with self.session.delete(url) as response:
                payload = await response.json()
                if response.status >= 400:
                    reason = payload.get("reason") if isinstance(payload, dict) else None
                    raise SipIndoorStationApiError(
                        f"DELETE /api/call_history/{history_id} failed: {response.status} {reason or ''}".strip()
                    )
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise SipIndoorStationApiError(f"DELETE /api/call_history/{history_id} failed: {exc}") from exc
        if not isinstance(payload, dict):
            return {"ok": True}
        return payload

    async def async_clear_call_history(self) -> dict[str, Any]:
        """Delete all call history entries from the add-on."""
        url = self.http_url("/api/call_history")
        try:
            async with self.session.delete(url) as response:
                payload = await response.json()
                if response.status >= 400:
                    reason = payload.get("reason") if isinstance(payload, dict) else None
                    raise SipIndoorStationApiError(
                        f"DELETE /api/call_history failed: {response.status} {reason or ''}".strip()
                    )
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise SipIndoorStationApiError(f"DELETE /api/call_history failed: {exc}") from exc
        if not isinstance(payload, dict):
            return {"ok": True}
        return payload

    async def async_command(self, command: str) -> dict[str, Any]:
        """Call a command endpoint."""
        url = self.http_url(f"/api/{command}")
        try:
            async with self.session.post(url) as response:
                try:
                    payload = await response.json()
                except aiohttp.ContentTypeError:
                    payload = {"ok": response.status < 400}
                if response.status >= 400:
                    reason = payload.get("reason") if isinstance(payload, dict) else None
                    raise SipIndoorStationApiError(
                        f"POST /api/{command} failed: {response.status} {reason or ''}".strip()
                    )
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise SipIndoorStationApiError(f"POST /api/{command} failed: {exc}") from exc
        if not isinstance(payload, dict):
            return {"ok": True}
        return payload

"""State coordinator for SIP Indoor Station."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SipIndoorStationApiClient, SipIndoorStationApiError
from .const import DOMAIN

LOGGER = logging.getLogger(__name__)


class SipIndoorStationCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate add-on state from HTTP polling and WebSocket push."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SipIndoorStationApiClient,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.client = client
        self._ws_task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch current state from the add-on."""
        try:
            return await self.client.async_get_state()
        except SipIndoorStationApiError as exc:
            raise UpdateFailed(str(exc)) from exc

    async def async_start(self) -> None:
        """Start WebSocket state listener."""
        if self._ws_task is None or self._ws_task.done():
            self._stopped.clear()
            self._ws_task = self.hass.loop.create_task(self._ws_loop())

    async def async_stop(self) -> None:
        """Stop WebSocket state listener."""
        self._stopped.set()
        if self._ws_task is not None:
            self._ws_task.cancel()
            await asyncio.gather(self._ws_task, return_exceptions=True)
            self._ws_task = None

    async def async_command(self, command: str) -> None:
        """Send command to the add-on and refresh state."""
        await self.client.async_command(command)
        await self.async_request_refresh()

    async def _ws_loop(self) -> None:
        """Maintain state WebSocket connection."""
        delay = 1.0
        while not self._stopped.is_set():
            try:
                async with self.client.session.ws_connect(self.client.ws_url("/api/ws")) as ws:
                    delay = 1.0
                    async for message in ws:
                        if self._stopped.is_set():
                            return
                        if message.type is aiohttp.WSMsgType.TEXT:
                            self._handle_ws_message(message.json())
                        elif message.type is aiohttp.WSMsgType.ERROR:
                            LOGGER.warning("state_ws_error error=%s", ws.exception())
                            break
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
                LOGGER.warning("state_ws_connection_failed error=%s", exc)
            if not self._stopped.is_set():
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)

    def _handle_ws_message(self, message: dict[str, Any]) -> None:
        """Apply a WebSocket message."""
        if message.get("type") == "state" and isinstance(message.get("state"), dict):
            self.async_set_updated_data(message["state"])
        elif message.get("type") == "event":
            LOGGER.debug("station_event event=%s", message)

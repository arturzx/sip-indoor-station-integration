"""HTTP/WebSocket proxy for SIP Indoor Station add-on WebRTC signaling."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp
from aiohttp import WSMsgType, web

from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant

from .api import SipIndoorStationApiClient

LOGGER = logging.getLogger(__name__)
WEBRTC_SESSION_TTL_SECONDS = 60.0
WEBRTC_SESSION_URL = "/api/sip_indoor_station/webrtc/session"
WEBRTC_CONFIG_URL = "/api/sip_indoor_station/webrtc/config"
WEBRTC_WS_URL = "/api/sip_indoor_station/webrtc/ws"


class SipIndoorStationProxy:
    """Proxy state and helpers."""

    def __init__(self, client: SipIndoorStationApiClient) -> None:
        """Initialize proxy."""
        self.client = client

    def create_signed_webrtc_urls(self) -> dict[str, object]:
        """Create short-lived Home Assistant signed WebRTC proxy URLs."""
        expiration = timedelta(seconds=WEBRTC_SESSION_TTL_SECONDS)
        return {
            "config_url": async_sign_path(self.client.hass, WEBRTC_CONFIG_URL, expiration),
            "ws_url": async_sign_path(self.client.hass, WEBRTC_WS_URL, expiration),
            "expires_in": int(WEBRTC_SESSION_TTL_SECONDS),
        }


def register_http_views(hass: HomeAssistant, proxy: SipIndoorStationProxy) -> None:
    """Register HTTP views."""
    hass.http.register_view(WebRtcSessionView(proxy))
    hass.http.register_view(WebRtcConfigView(proxy))
    hass.http.register_view(WebRtcWebSocketView(proxy))


class WebRtcSessionView(HomeAssistantView):
    """Create authenticated short-lived WebRTC proxy sessions."""

    url = WEBRTC_SESSION_URL
    name = "api:sip_indoor_station:webrtc_session"
    requires_auth = True

    def __init__(self, proxy: SipIndoorStationProxy) -> None:
        """Initialize view."""
        self.proxy = proxy

    async def post(self, _request: web.Request) -> web.Response:
        """Return short-lived Home Assistant signed proxy URLs."""
        return web.json_response(self.proxy.create_signed_webrtc_urls())


class WebRtcConfigView(HomeAssistantView):
    """Proxy WebRTC browser config."""

    url = WEBRTC_CONFIG_URL
    name = "api:sip_indoor_station:webrtc_config"
    requires_auth = True

    def __init__(self, proxy: SipIndoorStationProxy) -> None:
        """Initialize view."""
        self.proxy = proxy

    async def get(self, request: web.Request) -> web.Response:
        """Proxy WebRTC config request."""
        upstream_url = self.proxy.client.http_url("/webrtc/config")
        try:
            async with self.proxy.client.session.get(upstream_url) as response:
                body = await response.read()
                content_type = response.headers.get("Content-Type", "application/json")
                return web.Response(
                    body=body,
                    status=response.status,
                    content_type=content_type.partition(";")[0],
                )
        except aiohttp.ClientError as exc:
            LOGGER.warning("webrtc_config_proxy_failed url=%s error=%s", upstream_url, exc)
            return web.json_response(
                {"error": "webrtc_config_proxy_failed", "message": str(exc)},
                status=502,
            )


class WebRtcWebSocketView(HomeAssistantView):
    """Proxy WebRTC signaling WebSocket."""

    url = WEBRTC_WS_URL
    name = "api:sip_indoor_station:webrtc_ws"
    requires_auth = True

    def __init__(self, proxy: SipIndoorStationProxy) -> None:
        """Initialize view."""
        self.proxy = proxy

    async def get(self, request: web.Request) -> web.WebSocketResponse:
        """Proxy WebSocket signaling."""
        ws_server = web.WebSocketResponse(autoclose=False, autoping=False)
        await ws_server.prepare(request)

        upstream_url = self.proxy.client.ws_url("/webrtc/ws")
        try:
            async with self.proxy.client.session.ws_connect(
                upstream_url,
                autoclose=False,
                autoping=False,
            ) as ws_client:
                await asyncio.wait(
                    [
                        asyncio.create_task(_forward_websocket(ws_server, ws_client)),
                        asyncio.create_task(_forward_websocket(ws_client, ws_server)),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
        except aiohttp.ClientError as exc:
            LOGGER.warning("webrtc_ws_proxy_failed url=%s error=%s", upstream_url, exc)
            if not ws_server.closed:
                await ws_server.send_json(
                    {"type": "error", "message": f"WebRTC proxy failed: {exc}"}
                )
        finally:
            if not ws_server.closed:
                await ws_server.close()

        return ws_server


async def _forward_websocket(
    ws_from: web.WebSocketResponse | aiohttp.ClientWebSocketResponse,
    ws_to: web.WebSocketResponse | aiohttp.ClientWebSocketResponse,
) -> None:
    """Forward messages between WebSocket peers."""
    async for msg in ws_from:
        if ws_to.closed:
            return
        if msg.type is WSMsgType.TEXT:
            await ws_to.send_str(msg.data)
        elif msg.type is WSMsgType.BINARY:
            await ws_to.send_bytes(msg.data)
        elif msg.type is WSMsgType.PING:
            await ws_to.ping(msg.data)
        elif msg.type is WSMsgType.PONG:
            await ws_to.pong(msg.data)
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            await ws_to.close()
            return

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
from .coordinator import SipIndoorStationHistoryCoordinator

LOGGER = logging.getLogger(__name__)
WEBRTC_SESSION_TTL_SECONDS = 60.0
SNAPSHOT_URL_TTL_SECONDS = 300.0
WEBRTC_SESSION_URL = "/api/sip_indoor_station/webrtc/session"
WEBRTC_CONFIG_URL = "/api/sip_indoor_station/webrtc/config"
WEBRTC_WS_URL = "/api/sip_indoor_station/webrtc/ws"
CALL_HISTORY_URL = "/api/sip_indoor_station/call_history"
CALL_HISTORY_ENTRY_URL = "/api/sip_indoor_station/call_history/{history_id}"
CALL_HISTORY_SNAPSHOT_URL = "/api/sip_indoor_station/call_history/{history_id}/snapshot"


class SipIndoorStationProxy:
    """Proxy state and helpers."""

    def __init__(
        self,
        client: SipIndoorStationApiClient,
        history_coordinator: SipIndoorStationHistoryCoordinator | None = None,
    ) -> None:
        """Initialize proxy."""
        self.client = client
        self.history_coordinator = history_coordinator

    def create_signed_webrtc_urls(self) -> dict[str, object]:
        """Create short-lived Home Assistant signed WebRTC proxy URLs."""
        expiration = timedelta(seconds=WEBRTC_SESSION_TTL_SECONDS)
        return {
            "config_url": async_sign_path(self.client.hass, WEBRTC_CONFIG_URL, expiration),
            "ws_url": async_sign_path(self.client.hass, WEBRTC_WS_URL, expiration),
            "expires_in": int(WEBRTC_SESSION_TTL_SECONDS),
        }

    def signed_snapshot_url(self, history_id: str) -> str:
        """Create a short-lived signed snapshot URL."""
        path = CALL_HISTORY_SNAPSHOT_URL.format(history_id=history_id)
        return async_sign_path(self.client.hass, path, timedelta(seconds=SNAPSHOT_URL_TTL_SECONDS))

    async def async_refresh_history(self) -> None:
        """Refresh history coordinator after a proxied mutation."""
        if self.history_coordinator is not None:
            await self.history_coordinator.async_request_refresh()


def register_http_views(hass: HomeAssistant, proxy: SipIndoorStationProxy) -> None:
    """Register HTTP views."""
    hass.http.register_view(WebRtcSessionView(proxy))
    hass.http.register_view(WebRtcConfigView(proxy))
    hass.http.register_view(WebRtcWebSocketView(proxy))
    hass.http.register_view(CallHistoryCollectionView(proxy))
    hass.http.register_view(CallHistoryEntryView(proxy))
    hass.http.register_view(CallHistorySnapshotView(proxy))


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


class CallHistoryCollectionView(HomeAssistantView):
    """Proxy call history collection."""

    url = CALL_HISTORY_URL
    name = "api:sip_indoor_station:call_history"
    requires_auth = True

    def __init__(self, proxy: SipIndoorStationProxy) -> None:
        """Initialize view."""
        self.proxy = proxy

    async def get(self, request: web.Request) -> web.Response:
        """Proxy call history list request."""
        response = await _proxy_json_request(
            self.proxy.client,
            "GET",
            "/api/call_history",
            params=request.query,
        )
        if isinstance(response, web.Response):
            return response
        calls = response.get("calls")
        if isinstance(calls, list):
            response["calls"] = [_with_signed_snapshot_url(self.proxy, entry) for entry in calls]
        return web.json_response(response)

    async def delete(self, _request: web.Request) -> web.Response:
        """Proxy call history clear request."""
        response = await _proxy_http_request(self.proxy.client, "DELETE", "/api/call_history")
        if response.status < 400:
            await self.proxy.async_refresh_history()
        return response


class CallHistoryEntryView(HomeAssistantView):
    """Proxy one call history entry."""

    url = CALL_HISTORY_ENTRY_URL
    name = "api:sip_indoor_station:call_history_entry"
    requires_auth = True

    def __init__(self, proxy: SipIndoorStationProxy) -> None:
        """Initialize view."""
        self.proxy = proxy

    async def get(self, _request: web.Request, history_id: str) -> web.Response:
        """Proxy call history entry request."""
        response = await _proxy_json_request(self.proxy.client, "GET", f"/api/call_history/{history_id}")
        if isinstance(response, web.Response):
            return response
        return web.json_response(_with_signed_snapshot_url(self.proxy, response))

    async def delete(self, _request: web.Request, history_id: str) -> web.Response:
        """Proxy call history entry delete request."""
        response = await _proxy_http_request(self.proxy.client, "DELETE", f"/api/call_history/{history_id}")
        if response.status < 400:
            await self.proxy.async_refresh_history()
        return response


class CallHistorySnapshotView(HomeAssistantView):
    """Proxy one call history snapshot."""

    url = CALL_HISTORY_SNAPSHOT_URL
    name = "api:sip_indoor_station:call_history_snapshot"
    requires_auth = True

    def __init__(self, proxy: SipIndoorStationProxy) -> None:
        """Initialize view."""
        self.proxy = proxy

    async def get(self, _request: web.Request, history_id: str) -> web.Response:
        """Proxy call history snapshot request."""
        return await _proxy_http_request(self.proxy.client, "GET", f"/api/call_history/{history_id}/snapshot")


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


def _with_signed_snapshot_url(proxy: SipIndoorStationProxy, entry: object) -> object:
    """Replace add-on snapshot URL with a signed Home Assistant URL."""
    if not isinstance(entry, dict):
        return entry
    history_id = entry.get("id")
    if entry.get("has_snapshot") and isinstance(history_id, str):
        entry = dict(entry)
        entry["snapshot_url"] = proxy.signed_snapshot_url(history_id)
    return entry


async def _proxy_json_request(
    client: SipIndoorStationApiClient,
    method: str,
    path: str,
    *,
    params: object | None = None,
) -> dict[str, object] | web.Response:
    """Proxy one JSON request to the add-on."""
    upstream_url = client.http_url(path)
    try:
        async with client.session.request(method, upstream_url, params=params) as response:
            if response.status >= 400:
                body = await response.read()
                content_type = response.headers.get("Content-Type", "application/json")
                return web.Response(
                    body=body,
                    status=response.status,
                    content_type=content_type.partition(";")[0],
                )
            payload = await response.json()
    except aiohttp.ClientError as exc:
        LOGGER.warning("addon_json_proxy_failed method=%s url=%s error=%s", method, upstream_url, exc)
        return web.json_response(
            {"error": "addon_json_proxy_failed", "message": str(exc)},
            status=502,
        )
    if not isinstance(payload, dict):
        return web.json_response({"error": "invalid_json_payload"}, status=502)
    return payload


async def _proxy_http_request(
    client: SipIndoorStationApiClient,
    method: str,
    path: str,
    *,
    params: object | None = None,
) -> web.Response:
    """Proxy one HTTP request to the add-on."""
    upstream_url = client.http_url(path)
    try:
        async with client.session.request(method, upstream_url, params=params) as response:
            body = await response.read()
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            return web.Response(
                body=body,
                status=response.status,
                content_type=content_type.partition(";")[0],
            )
    except aiohttp.ClientError as exc:
        LOGGER.warning("addon_http_proxy_failed method=%s url=%s error=%s", method, upstream_url, exc)
        return web.json_response(
            {"error": "addon_http_proxy_failed", "message": str(exc)},
            status=502,
        )

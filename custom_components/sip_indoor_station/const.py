"""Constants for the SIP Indoor Station integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "sip_indoor_station"

CONF_ADDON_SLUG = "addon_slug"
CONF_ADDON_URL = "addon_url"
CONF_DEVICE_NAME = "device_name"

DEFAULT_ADDON_SLUG = "c1b42bc7_sip_indoor_station"
DEFAULT_ADDON_PORT = 8080
DEFAULT_DEVICE_NAME = "Door station"

DATA_CLIENT = "client"
DATA_COORDINATOR = "coordinator"
DATA_PROXY = "proxy"

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

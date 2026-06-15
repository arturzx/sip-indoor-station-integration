"""Config flow for SIP Indoor Station."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_ADDON_SLUG,
    CONF_ADDON_URL,
    CONF_DEVICE_NAME,
    DEFAULT_ADDON_SLUG,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
)


class SipIndoorStationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a SIP Indoor Station config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            device_name = user_input[CONF_DEVICE_NAME].strip() or DEFAULT_DEVICE_NAME
            return self.async_create_entry(
                title=device_name,
                data={
                    CONF_ADDON_SLUG: user_input[CONF_ADDON_SLUG],
                    CONF_ADDON_URL: user_input.get(CONF_ADDON_URL, "").strip(),
                    CONF_DEVICE_NAME: device_name,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): str,
                    vol.Required(CONF_ADDON_SLUG, default=DEFAULT_ADDON_SLUG): str,
                    vol.Optional(CONF_ADDON_URL, default=""): str,
                }
            ),
        )

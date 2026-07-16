"""Config flow for LabelBerry."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    LabelBerryApiError,
    LabelBerryClient,
    LabelBerryConnectionError,
    LabelBerryResponseError,
    normalize_base_url,
)
from .const import CONF_URL, DOMAIN


def _url_schema(default: str = "http://localhost:8000") -> vol.Schema:
    return vol.Schema({vol.Required(CONF_URL, default=default): cv.string})


class LabelBerryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one LabelBerry server."""

    VERSION = 1

    async def _async_validate_url(self, value: str) -> str:
        try:
            url = normalize_base_url(value)
        except ValueError as err:
            raise LabelBerryResponseError(str(err)) from err
        client = LabelBerryClient(async_get_clientsession(self.hass), url)
        await client.async_get_status()
        return url

    @override
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle initial setup."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = await self._async_validate_url(user_input[CONF_URL])
            except LabelBerryConnectionError:
                errors["base"] = "cannot_connect"
            except LabelBerryApiError:
                errors["base"] = "invalid_response"
            else:
                return self.async_create_entry(title="LabelBerry", data={CONF_URL: url})

        return self.async_show_form(
            step_id="user",
            data_schema=_url_schema(
                user_input[CONF_URL] if user_input else "http://localhost:8000"
            ),
            errors=errors,
        )

    @override
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate and update the LabelBerry server URL."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = await self._async_validate_url(user_input[CONF_URL])
            except LabelBerryConnectionError:
                errors["base"] = "cannot_connect"
            except LabelBerryApiError:
                errors["base"] = "invalid_response"
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_URL: url})

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_url_schema(user_input[CONF_URL] if user_input else entry.data[CONF_URL]),
            errors=errors,
        )

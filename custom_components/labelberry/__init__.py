"""Home Assistant integration for LabelBerry."""

from dataclasses import dataclass

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import (
    LabelBerryBackendError,
    LabelBerryClient,
    LabelBerryConnectionError,
    LabelBerryResponseError,
)
from .const import CONF_URL, DOMAIN, PLATFORMS, SERVICE_PRINT_LABEL
from .coordinator import LabelBerryCoordinator

PRINT_LABEL_SCHEMA = vol.Schema(
    {
        vol.Required("text"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("left"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("right"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("copies", default=1): vol.All(cv.positive_int, vol.Range(min=1, max=100)),
    }
)


@dataclass(slots=True)
class LabelBerryRuntimeData:
    """Objects owned by one loaded LabelBerry config entry."""

    client: LabelBerryClient
    coordinator: LabelBerryCoordinator


type LabelBerryConfigEntry = ConfigEntry[LabelBerryRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the LabelBerry integration and its print action."""

    async def async_print_label(call: ServiceCall) -> None:
        loaded_entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        if len(loaded_entries) != 1:
            raise ServiceValidationError(
                "LabelBerry must be configured and loaded before printing."
            )

        runtime_data: LabelBerryRuntimeData = loaded_entries[0].runtime_data
        try:
            await runtime_data.client.async_quick_print(
                call.data["text"],
                copies=call.data["copies"],
                left=call.data.get("left"),
                right=call.data.get("right"),
            )
        except LabelBerryConnectionError as err:
            raise HomeAssistantError("Unable to reach the LabelBerry server.") from err
        except LabelBerryResponseError as err:
            raise HomeAssistantError("LabelBerry returned an unexpected response.") from err
        except LabelBerryBackendError as err:
            raise HomeAssistantError(f"{err.code}: {err.message}") from err

    if not hass.services.has_service(DOMAIN, SERVICE_PRINT_LABEL):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PRINT_LABEL,
            async_print_label,
            schema=PRINT_LABEL_SCHEMA,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: LabelBerryConfigEntry) -> bool:
    """Set up LabelBerry from a config entry."""
    client = LabelBerryClient(async_get_clientsession(hass), entry.data[CONF_URL])
    coordinator = LabelBerryCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = LabelBerryRuntimeData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LabelBerryConfigEntry) -> bool:
    """Unload a LabelBerry config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

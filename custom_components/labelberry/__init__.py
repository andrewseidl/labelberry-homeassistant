"""Home Assistant integration for LabelBerry."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LabelBerryClient
from .const import CONF_URL, PLATFORMS
from .coordinator import LabelBerryCoordinator


@dataclass(slots=True)
class LabelBerryRuntimeData:
    """Objects owned by one loaded LabelBerry config entry."""

    client: LabelBerryClient
    coordinator: LabelBerryCoordinator


type LabelBerryConfigEntry = ConfigEntry[LabelBerryRuntimeData]


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

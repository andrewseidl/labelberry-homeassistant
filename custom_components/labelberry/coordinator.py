"""Status coordinator for LabelBerry."""

import logging
from datetime import timedelta
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LabelBerryApiError, LabelBerryClient, LabelBerryStatus
from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class LabelBerryCoordinator(DataUpdateCoordinator[LabelBerryStatus]):
    """Coordinate LabelBerry status polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: LabelBerryClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
            always_update=False,
        )
        self.client = client

    @override
    async def _async_update_data(self) -> LabelBerryStatus:
        try:
            return await self.client.async_get_status()
        except LabelBerryApiError as err:
            raise UpdateFailed(str(err)) from err

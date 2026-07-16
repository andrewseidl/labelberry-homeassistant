from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.labelberry import LabelBerryRuntimeData
from custom_components.labelberry.api import LabelBerryConnectionError, LabelBerryStatus
from custom_components.labelberry.const import CONF_URL, DOMAIN, SCAN_INTERVAL_SECONDS

BASE_URL = "http://labelberry.local:8000"
STATUS = LabelBerryStatus(connected=True, tape_width_mm=12.0, backend="usb")


async def test_setup_stores_runtime_data_and_unloads(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="LabelBerry", data={CONF_URL: BASE_URL})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.labelberry.api.LabelBerryClient.async_get_status",
        new=AsyncMock(return_value=STATUS),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, LabelBerryRuntimeData)
    assert entry.runtime_data.client.base_url == BASE_URL
    assert entry.runtime_data.coordinator.update_interval.total_seconds() == SCAN_INTERVAL_SECONDS

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_initial_connection_failure_schedules_setup_retry(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="LabelBerry", data={CONF_URL: BASE_URL})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.labelberry.api.LabelBerryClient.async_get_status",
        new=AsyncMock(side_effect=LabelBerryConnectionError("offline")),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY

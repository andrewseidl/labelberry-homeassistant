from unittest.mock import AsyncMock, patch

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.labelberry.api import LabelBerryStatus
from custom_components.labelberry.const import CONF_URL, DOMAIN

BASE_URL = "http://labelberry.local:8000"
CONNECTED = LabelBerryStatus(connected=True, tape_width_mm=12.0, backend="usb")
DISCONNECTED = LabelBerryStatus(connected=False, tape_width_mm=None, backend="usb")


async def _setup_entry(hass, status: LabelBerryStatus = CONNECTED):
    entry = MockConfigEntry(domain=DOMAIN, title="LabelBerry", data={CONF_URL: BASE_URL})
    entry.add_to_hass(hass)
    with patch(
        "custom_components.labelberry.api.LabelBerryClient.async_get_status",
        new=AsyncMock(return_value=status),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_status_sensor_exposes_state_attributes_and_device(hass) -> None:
    entry = await _setup_entry(hass)

    state = hass.states.get("sensor.labelberry_status")
    assert state is not None
    assert state.state == "connected"
    assert state.attributes["tape_width_mm"] == 12.0
    assert state.attributes["backend"] == "usb"

    entity = er.async_get(hass).async_get("sensor.labelberry_status")
    assert entity is not None
    assert entity.unique_id == f"{entry.entry_id}_status"

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None
    assert device.name == "LabelBerry"
    assert device.configuration_url == BASE_URL


async def test_reachable_disconnected_printer_remains_available(hass) -> None:
    entry = await _setup_entry(hass, DISCONNECTED)

    state = hass.states.get("sensor.labelberry_status")
    assert state is not None
    assert state.state == "disconnected"
    assert state.attributes["tape_width_mm"] is None
    assert state.state != "unavailable"
    assert entry.runtime_data.coordinator.last_update_success


async def test_coordinator_failure_marks_sensor_unavailable(hass) -> None:
    entry = await _setup_entry(hass)

    entry.runtime_data.coordinator.async_set_update_error(UpdateFailed("offline"))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.labelberry_status")
    assert state is not None
    assert state.state == "unavailable"

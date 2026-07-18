from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.labelberry.api import (
    LabelBerryBackendError,
    LabelBerryConnectionError,
    LabelBerryResponseError,
    LabelBerryStatus,
    QueuedJob,
)
from custom_components.labelberry.const import (
    CONF_URL,
    DOMAIN,
    SERVICE_PRINT_LABEL,
    SERVICE_PRINT_TEMPLATE,
)

BASE_URL = "http://labelberry.local:8000"
STATUS = LabelBerryStatus(connected=True, tape_width_mm=12.0, backend="usb")
JOB = QueuedJob(id="abc123", status="queued", copies=1, error=None)


async def _setup_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, title="LabelBerry", data={CONF_URL: BASE_URL})
    entry.add_to_hass(hass)
    with patch(
        "custom_components.labelberry.api.LabelBerryClient.async_get_status",
        new=AsyncMock(return_value=STATUS),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_print_action_forwards_multiline_text_and_unicode_flanks(hass) -> None:
    entry = await _setup_entry(hass)
    entry.runtime_data.client.async_quick_print = AsyncMock(return_value=JOB)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_PRINT_LABEL,
        {"text": "Cold\nWash", "copies": 2, "left": "🧺", "right": "🌬️"},
        blocking=True,
    )

    entry.runtime_data.client.async_quick_print.assert_awaited_once_with(
        "Cold\nWash", copies=2, left="🧺", right="🌬️"
    )


async def test_print_action_defaults_copies_and_omits_flanks(hass) -> None:
    entry = await _setup_entry(hass)
    entry.runtime_data.client.async_quick_print = AsyncMock(return_value=JOB)

    await hass.services.async_call(DOMAIN, SERVICE_PRINT_LABEL, {"text": "Pantry"}, blocking=True)

    entry.runtime_data.client.async_quick_print.assert_awaited_once_with(
        "Pantry", copies=1, left=None, right=None
    )


@pytest.mark.parametrize(
    "data",
    [
        {"text": ""},
        {"text": "ok", "left": ""},
        {"text": "ok", "right": ""},
        {"text": "ok", "copies": 0},
        {"text": "ok", "copies": 101},
    ],
)
async def test_print_action_rejects_invalid_fields_before_calling_client(hass, data) -> None:
    entry = await _setup_entry(hass)
    entry.runtime_data.client.async_quick_print = AsyncMock(return_value=JOB)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(DOMAIN, SERVICE_PRINT_LABEL, data, blocking=True)

    entry.runtime_data.client.async_quick_print.assert_not_awaited()


async def test_print_action_requires_loaded_entry(hass) -> None:
    assert await async_setup_component(hass, DOMAIN, {})

    with pytest.raises(ServiceValidationError, match="configured and loaded"):
        await hass.services.async_call(
            DOMAIN, SERVICE_PRINT_LABEL, {"text": "Pantry"}, blocking=True
        )


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (LabelBerryConnectionError("offline"), "Unable to reach"),
        (LabelBerryResponseError("bad JSON"), "unexpected response"),
        (LabelBerryBackendError("render_error", "too wide", 422), "render_error: too wide"),
    ],
)
async def test_print_action_surfaces_errors_without_retry(hass, error, message) -> None:
    entry = await _setup_entry(hass)
    entry.runtime_data.client.async_quick_print = AsyncMock(side_effect=error)

    with pytest.raises(HomeAssistantError, match=message):
        await hass.services.async_call(
            DOMAIN, SERVICE_PRINT_LABEL, {"text": "Pantry"}, blocking=True
        )

    entry.runtime_data.client.async_quick_print.assert_awaited_once()


async def test_print_template_action_dispatches_once(hass) -> None:
    entry = await _setup_entry(hass)
    entry.runtime_data.client.async_print_template = AsyncMock(return_value=JOB)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_PRINT_TEMPLATE,
        {"template": "Leftovers", "variables": {"food": "Curry"}, "copies": 2},
        blocking=True,
    )

    entry.runtime_data.client.async_print_template.assert_awaited_once_with(
        "Leftovers", {"food": "Curry"}, copies=2
    )


async def test_print_template_action_defaults_variables_and_copies(hass) -> None:
    entry = await _setup_entry(hass)
    entry.runtime_data.client.async_print_template = AsyncMock(return_value=JOB)

    await hass.services.async_call(
        DOMAIN, SERVICE_PRINT_TEMPLATE, {"template": "Leftovers"}, blocking=True
    )

    entry.runtime_data.client.async_print_template.assert_awaited_once_with(
        "Leftovers", {}, copies=1
    )


@pytest.mark.parametrize(
    "data",
    [
        {"template": ""},
        {"template": "T", "variables": []},
        {"template": "T", "variables": {1: "x"}},
        {"template": "T", "variables": {"x": 1}},
        {"template": "T", "copies": 0},
        {"template": "T", "copies": 101},
    ],
)
async def test_print_template_rejects_invalid_fields(hass, data) -> None:
    entry = await _setup_entry(hass)
    entry.runtime_data.client.async_print_template = AsyncMock(return_value=JOB)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(DOMAIN, SERVICE_PRINT_TEMPLATE, data, blocking=True)

    entry.runtime_data.client.async_print_template.assert_not_awaited()


async def test_print_template_requires_loaded_entry(hass) -> None:
    assert await async_setup_component(hass, DOMAIN, {})

    with pytest.raises(ServiceValidationError, match="configured and loaded"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PRINT_TEMPLATE,
            {"template": "Leftovers"},
            blocking=True,
        )


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (LabelBerryConnectionError("offline"), "Unable to reach"),
        (LabelBerryResponseError("bad JSON"), "unexpected response"),
        (LabelBerryBackendError("render_error", "too wide", 422), "render_error: too wide"),
    ],
)
async def test_print_template_surfaces_errors_without_retry(hass, error, message) -> None:
    entry = await _setup_entry(hass)
    entry.runtime_data.client.async_print_template = AsyncMock(side_effect=error)

    with pytest.raises(HomeAssistantError, match=message):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PRINT_TEMPLATE,
            {"template": "Leftovers"},
            blocking=True,
        )

    entry.runtime_data.client.async_print_template.assert_awaited_once()

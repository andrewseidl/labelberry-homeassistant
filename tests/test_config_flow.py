from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.labelberry.api import (
    LabelBerryConnectionError,
    LabelBerryResponseError,
    LabelBerryStatus,
)
from custom_components.labelberry.const import CONF_URL, DOMAIN

STATUS = LabelBerryStatus(connected=True, tape_width_mm=12.0, backend="usb")


async def test_user_flow_shows_form(hass) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_flow_creates_normalized_entry(hass) -> None:
    with (
        patch(
            "custom_components.labelberry.config_flow.LabelBerryClient.async_get_status",
            new=AsyncMock(return_value=STATUS),
        ) as get_status,
        patch(
            "custom_components.labelberry.async_setup_entry",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_URL: " HTTP://LabelBerry.Local:8000/prefix/?ignored=1#fragment "},
        )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "LabelBerry"
    assert result["data"] == {CONF_URL: "http://labelberry.local:8000/prefix"}
    get_status.assert_awaited_once()


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (LabelBerryConnectionError("offline"), "cannot_connect"),
        (LabelBerryResponseError("bad response"), "invalid_response"),
    ],
)
async def test_user_flow_maps_validation_errors(hass, side_effect, error) -> None:
    with patch(
        "custom_components.labelberry.config_flow.LabelBerryClient.async_get_status",
        new=AsyncMock(side_effect=side_effect),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_URL: "http://labelberry.local:8000"},
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_user_flow_rejects_invalid_url(hass) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_URL: "ftp://labelberry.local"},
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_response"}


async def test_user_flow_aborts_when_entry_exists(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="LabelBerry", data={CONF_URL: "http://old"})
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_reconfigure_updates_and_reloads_entry(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="LabelBerry", data={CONF_URL: "http://old"})
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.labelberry.config_flow.LabelBerryClient.async_get_status",
            new=AsyncMock(return_value=STATUS),
        ),
        patch.object(hass.config_entries, "async_reload", AsyncMock(return_value=True)) as reload,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={CONF_URL: "https://NEW.local/base/"},
        )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_URL: "https://new.local/base"}
    reload.assert_awaited_once_with(entry.entry_id)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_failed_reconfigure_preserves_existing_url(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="LabelBerry", data={CONF_URL: "http://old"})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.labelberry.config_flow.LabelBerryClient.async_get_status",
        new=AsyncMock(side_effect=LabelBerryConnectionError("offline")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={CONF_URL: "http://new"},
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data == {CONF_URL: "http://old"}


def _discovery_info(host="10.10.10.100", port=8000):
    from ipaddress import ip_address

    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        hostname="marlin.local.",
        name="LabelBerry (marlin)._labelberry._tcp.local.",
        port=port,
        type="_labelberry._tcp.local.",
        properties={"api": "/api", "path": "/"},
    )


async def test_zeroconf_flow_discovers_confirms_and_creates_entry(hass) -> None:
    with (
        patch(
            "custom_components.labelberry.config_flow.LabelBerryClient.async_get_status",
            new=AsyncMock(return_value=STATUS),
        ) as get_status,
        patch(
            "custom_components.labelberry.async_setup_entry",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=_discovery_info(),
        )

        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "zeroconf_confirm"
        assert result["description_placeholders"] == {"url": "http://10.10.10.100:8000"}

        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={})

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: "http://10.10.10.100:8000"}
    get_status.assert_awaited_once()


async def test_zeroconf_aborts_when_already_configured(hass) -> None:
    MockConfigEntry(domain=DOMAIN, data={CONF_URL: "http://10.0.0.1:8000"}).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_discovery_info(),
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_zeroconf_aborts_when_discovered_server_does_not_validate(hass) -> None:
    with patch(
        "custom_components.labelberry.config_flow.LabelBerryClient.async_get_status",
        new=AsyncMock(side_effect=LabelBerryConnectionError("nope")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=_discovery_info(),
        )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"

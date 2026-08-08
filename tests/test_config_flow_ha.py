"""Home Assistant config flow tests."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteogalicia_tides.const import (
    CONF_ID_PORT,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)


async def test_user_flow_creates_port_entry(hass):
    """A selected port creates a stable config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with patch(
        "custom_components.meteogalicia_tides.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ID_PORT: "1"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "A Coruña"
    assert result["data"] == {CONF_ID_PORT: "1"}
    assert result["result"].unique_id == "1"


async def test_user_flow_rejects_duplicate_port(hass):
    """The UI cannot create two entries for the same port ID."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="1", data={CONF_ID_PORT: "1"}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ID_PORT: "1"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_yaml_import_creates_entry_and_normalizes_id(hass):
    """Legacy YAML continues to import numeric IDs without changing them."""
    with patch(
        "custom_components.meteogalicia_tides.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_ID_PORT: "03", CONF_SCAN_INTERVAL: 1800},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vigo"
    assert result["data"] == {
        CONF_ID_PORT: "3",
        CONF_SCAN_INTERVAL: 1800,
    }
    assert result["result"].unique_id == "3"


async def test_yaml_import_rejects_duplicate_port(hass):
    """Repeated YAML imports update the interval without duplicating."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="3", data={CONF_ID_PORT: "3"}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={CONF_ID_PORT: "3", CONF_SCAN_INTERVAL: 1700},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data == {
        CONF_ID_PORT: "3",
        CONF_SCAN_INTERVAL: 1700,
    }


async def test_options_flow_updates_scan_interval(hass):
    """The polling interval can be changed without replacing the entry."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_ID_PORT: "1"})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 1800}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SCAN_INTERVAL: 1800}

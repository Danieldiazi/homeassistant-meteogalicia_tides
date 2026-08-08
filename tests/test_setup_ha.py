"""Full Home Assistant setup and YAML import tests."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteogalicia_tides.const import CONF_ID_PORT, DOMAIN
from custom_components.meteogalicia_tides.sensor import async_setup_platform

from .test_coordinator_ha import VALID_RESPONSE


async def test_full_entry_setup_entities_and_unload(hass):
    """Set up, expose, and unload a real integration entry."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_ID_PORT: "1"})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.meteogalicia_tides.coordinator."
        "MeteoGaliciaTidesCoordinator._async_update_data",
        new=AsyncMock(return_value=VALID_RESPONSE),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.data == VALID_RESPONSE
    assert entry.runtime_data.update_interval == timedelta(seconds=30)
    states = [
        state
        for state in hass.states.async_all("sensor")
        if state.attributes.get("integration") == DOMAIN
    ]
    assert len(states) == 1
    assert states[0].state in {"High tide at 23:59", "Low tide at 01:00"}

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_yaml_setup_waits_for_import_and_preserves_interval(hass):
    """Legacy YAML import is awaited and retains its exact interval."""
    flow_init = AsyncMock()
    with patch.object(hass.config_entries.flow, "async_init", flow_init):
        await async_setup_platform(
            hass,
            {
                CONF_ID_PORT: "3",
                CONF_SCAN_INTERVAL: timedelta(seconds=1800),
            },
            AsyncMock(),
        )

    flow_init.assert_awaited_once()
    assert flow_init.await_args.kwargs["data"] == {
        CONF_ID_PORT: "3",
        CONF_SCAN_INTERVAL: 1800,
    }

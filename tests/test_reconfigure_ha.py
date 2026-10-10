"""Reconfiguration preserves options, rejects duplicates and cleans old resources."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteogalicia_tides.const import (
    CONF_ID_PORT,
    CONF_RESET_ENTITIES,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

from .test_coordinator_ha import VALID_RESPONSE


async def start_reconfigure(hass, entry):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )


@pytest.mark.parametrize("port", ["1", "3"])
async def test_reconfigure_preserves_entry_and_options_with_one_reload(hass, port):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        title="A Coruña",
        data={CONF_ID_PORT: "1", CONF_SCAN_INTERVAL: 1200},
        options={CONF_SCAN_INTERVAL: 1800},
    )
    entry.add_to_hass(hass)
    result = await start_reconfigure(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    with (
        patch(
            "custom_components.meteogalicia_tides.config_flow._get_forecast_tide_data_from_api",
            return_value=VALID_RESPONSE,
        ),
        patch.object(
            hass.config_entries, "async_reload", AsyncMock(return_value=True)
        ) as reload,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ID_PORT: port}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == port
    assert entry.title == ("Vigo" if port == "3" else "A Coruña")
    assert entry.data[CONF_ID_PORT] == port
    assert entry.data[CONF_SCAN_INTERVAL] == 1200
    assert entry.options == {CONF_SCAN_INTERVAL: 1800}
    assert bool(entry.data.get(CONF_RESET_ENTITIES)) == (port != "1")
    reload.assert_awaited_once_with(entry.entry_id)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


@pytest.mark.parametrize("unique_id", ["3", None])
async def test_reconfigure_rejects_existing_and_legacy_duplicate_ports(hass, unique_id):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="1", data={CONF_ID_PORT: "1"})
    entry.add_to_hass(hass)
    other = MockConfigEntry(
        domain=DOMAIN, unique_id=unique_id, data={CONF_ID_PORT: "3"}
    )
    other.add_to_hass(hass)
    result = await start_reconfigure(hass, entry)
    with patch(
        "custom_components.meteogalicia_tides.config_flow._get_forecast_tide_data_from_api"
    ) as request:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ID_PORT: "3"}
        )
    assert result["reason"] == "already_configured"
    assert entry.data == {CONF_ID_PORT: "1"}
    request.assert_not_called()


@pytest.mark.parametrize(
    "response,error",
    [
        (None, "invalid_response"),
        ({}, "invalid_response"),
        (OSError("offline"), "cannot_connect"),
    ],
)
async def test_failed_reconfigure_keeps_original_port(hass, response, error):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="1", data={CONF_ID_PORT: "1"})
    entry.add_to_hass(hass)
    result = await start_reconfigure(hass, entry)
    with patch.object(
        hass,
        "async_add_executor_job",
        AsyncMock(
            side_effect=response if isinstance(response, Exception) else None,
            return_value=response,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ID_PORT: "3"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert entry.unique_id == "1"
    assert entry.data == {CONF_ID_PORT: "1"}


async def test_changing_port_replaces_only_that_entries_entities_and_device(
    hass, freezer
):
    freezer.move_to("2026-08-08T12:00:00Z")
    entry = MockConfigEntry(domain=DOMAIN, unique_id="1", data={CONF_ID_PORT: "1"})
    other = MockConfigEntry(domain=DOMAIN, unique_id="2", data={CONF_ID_PORT: "2"})
    entry.add_to_hass(hass)
    other.add_to_hass(hass)
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    with patch(
        "custom_components.meteogalicia_tides.coordinator.MeteoGaliciaTidesCoordinator._async_update_data",
        new=AsyncMock(return_value=VALID_RESPONSE),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert other.state is config_entries.ConfigEntryState.LOADED
        old_ids = {
            entity.unique_id
            for entity in er.async_entries_for_config_entry(entities, entry.entry_id)
        }
        other_ids = {
            entity.entity_id
            for entity in er.async_entries_for_config_entry(entities, other.entry_id)
        }
        old_devices = {
            device.id
            for device in dr.async_entries_for_config_entry(devices, entry.entry_id)
        }
        result = await start_reconfigure(hass, entry)
        with patch(
            "custom_components.meteogalicia_tides.config_flow._get_forecast_tide_data_from_api",
            return_value=VALID_RESPONSE,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_ID_PORT: "3"}
            )
            await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert not old_devices.intersection(devices.devices)
    assert other_ids.issubset(entities.entities)
    assert CONF_RESET_ENTITIES not in entry.data
    new_entities = er.async_entries_for_config_entry(entities, entry.entry_id)
    assert not old_ids.intersection(entity.unique_id for entity in new_entities)
    assert len(new_entities) == len(old_ids)
    assert all(entity.unique_id.endswith("_id_3") for entity in new_entities)

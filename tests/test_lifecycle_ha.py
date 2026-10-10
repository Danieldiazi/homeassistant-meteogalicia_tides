"""HTTP clients are reused and closed safely, including failed setup."""

import asyncio
from threading import Event
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteogalicia_tides import async_setup_entry, async_unload_entry
from custom_components.meteogalicia_tides.const import CONF_ID_PORT, DOMAIN
from custom_components.meteogalicia_tides.coordinator import (
    MeteoGaliciaTidesCoordinator,
    _get_forecast_tide_data_from_api,
)

from .test_coordinator_ha import VALID_RESPONSE


async def test_refresh_reuses_client_and_session_and_shutdown_closes_once(hass):
    session = Mock()
    client = Mock()
    client.get_forecast_tide.return_value = VALID_RESPONSE
    with (
        patch(
            "custom_components.meteogalicia_tides.coordinator.requests.Session",
            return_value=session,
        ) as create_session,
        patch(
            "custom_components.meteogalicia_tides.coordinator.MeteoGalicia",
            return_value=client,
        ) as create_client,
    ):
        coordinator = MeteoGaliciaTidesCoordinator(hass, "3")
        assert await coordinator._async_update_data() == VALID_RESPONSE
        assert await coordinator._async_update_data() == VALID_RESPONSE
        create_session.assert_called_once_with()
        create_client.assert_called_once()
        assert create_client.call_args.kwargs["session"] is session
        assert client.get_forecast_tide.call_count == 2
        await coordinator.async_shutdown()
        await coordinator.async_shutdown()
    session.close.assert_called_once_with()
    with pytest.raises(RuntimeError, match="shut down"):
        coordinator._get_forecast()
    assert client.get_forecast_tide.call_count == 2


async def test_shutdown_waits_for_running_request_before_closing_session(hass):
    started, finish = Event(), Event()
    session = Mock()

    def request(_port):
        started.set()
        assert finish.wait(5)
        session.close.assert_not_called()
        return VALID_RESPONSE

    with (
        patch(
            "custom_components.meteogalicia_tides.coordinator.requests.Session",
            return_value=session,
        ),
        patch("custom_components.meteogalicia_tides.coordinator.MeteoGalicia") as api,
    ):
        api.return_value.get_forecast_tide.side_effect = request
        coordinator = MeteoGaliciaTidesCoordinator(hass, "3")
        refresh = asyncio.create_task(coordinator._async_update_data())
        try:
            assert await asyncio.to_thread(started.wait, 5)
            shutdown = asyncio.create_task(coordinator.async_shutdown())
            await asyncio.sleep(0)
            session.close.assert_not_called()
        finally:
            finish.set()
        await refresh
        await shutdown
    session.close.assert_called_once_with()


async def test_failed_first_refresh_closes_session(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_ID_PORT: "3"})
    entry.add_to_hass(hass)
    session = Mock()
    with (
        patch(
            "custom_components.meteogalicia_tides.coordinator.requests.Session",
            return_value=session,
        ),
        patch.object(
            MeteoGaliciaTidesCoordinator,
            "async_config_entry_first_refresh",
            AsyncMock(side_effect=ConfigEntryNotReady("offline")),
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)
    session.close.assert_called_once_with()


async def test_failed_platform_unload_keeps_session_available(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_ID_PORT: "3"})
    entry.runtime_data = Mock(async_shutdown=AsyncMock())
    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    ):
        assert not await async_unload_entry(hass, entry)
    entry.runtime_data.async_shutdown.assert_not_awaited()


def test_configuration_validation_closes_its_temporary_session():
    session = Mock()
    with (
        patch(
            "custom_components.meteogalicia_tides.coordinator.requests.Session"
        ) as create,
        patch("custom_components.meteogalicia_tides.coordinator.MeteoGalicia") as api,
    ):
        create.return_value.__enter__.return_value = session
        api.return_value.get_forecast_tide.return_value = VALID_RESPONSE
        assert _get_forecast_tide_data_from_api("3") == VALID_RESPONSE
    assert api.call_args.kwargs["session"] is session
    create.return_value.__exit__.assert_called_once()

"""Local tide transitions between network polls."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.meteogalicia_tides.const import (
    CONF_ID_PORT,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.meteogalicia_tides.coordinator import (
    MeteoGaliciaTidesCoordinator,
)
from custom_components.meteogalicia_tides.sensor import _create_entities
from custom_components.meteogalicia_tides.tide import TIDE_TIME_ZONE

from .test_coordinator_ha import VALID_RESPONSE


async def test_expired_forecast_retries_before_next_daily_poll(hass, freezer):
    freezer.move_to("2026-08-10T12:00:00Z")
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1", timedelta(days=1))
    coordinator.data = VALID_RESPONSE
    with patch(
        "custom_components.meteogalicia_tides.coordinator.async_track_point_in_time"
    ) as track:
        remove = coordinator.async_add_listener(Mock())
        assert track.call_args.args[2] == datetime(
            2026, 8, 10, 14, 15, tzinfo=TIDE_TIME_ZONE
        )
        remove()
        track.return_value.assert_called_once()
    await coordinator.async_shutdown()


async def test_tide_boundary_updates_published_state_without_poll(hass, freezer):
    freezer.move_to("2026-08-08T21:58:00Z")
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_ID_PORT: "1"}, options={CONF_SCAN_INTERVAL: 86400}
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.meteogalicia_tides.coordinator."
        "MeteoGalicia.get_forecast_tide",
        return_value=VALID_RESPONSE,
    ) as fetch:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        state = next(
            s
            for s in hass.states.async_all("sensor")
            if s.attributes.get("integration") == DOMAIN
        )
        assert state.state == "High tide at 23:59"
        assert fetch.call_count == 1
        freezer.move_to("2026-08-08T21:59:01Z")
        async_fire_time_changed(hass, datetime(2026, 8, 8, 21, 59, 1, tzinfo=UTC))
        await hass.async_block_till_done()
        assert hass.states.get(state.entity_id).state == "Low tide at 01:00"
        assert fetch.call_count == 1
        assert entry.runtime_data.update_interval == timedelta(seconds=86400)
        coordinator = entry.runtime_data
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert coordinator._unsub_transition is None


async def test_midnight_refreshes_window_and_keeps_cached_dates(hass, freezer):
    freezer.move_to("2026-08-08T21:58:00Z")
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1", timedelta(days=1))
    coordinator.data = dict(VALID_RESPONSE)
    coordinator.data["tomorrowTides"] = [
        VALID_RESPONSE["tomorrowFirstTide"],
        {"@hora": "13:00", "@idTipoMarea": "1"},
    ]
    listener = Mock()
    remove = coordinator.async_add_listener(listener)
    with patch.object(coordinator, "async_request_refresh", AsyncMock()) as refresh:
        freezer.move_to("2026-08-08T22:00:01Z")
        coordinator._async_time_transition(datetime(2026, 8, 8, 22, 0, 1, tzinfo=UTC))
        await hass.async_block_till_done()
        refresh.assert_awaited_once()
        listener.assert_called_once()
        entities = _create_entities("1", coordinator)
        assert entities[0].native_value == "Low tide at 01:00"
        assert entities[1].native_value.astimezone(UTC) == datetime(
            2026, 8, 8, 23, tzinfo=UTC
        )
        assert entities[7].native_value == 2
        freezer.move_to("2026-08-10T12:00:00Z")
        assert all(entity.native_value is None for entity in entities)
    remove()
    remove()
    assert coordinator._unsub_transition is None
    await coordinator.async_shutdown()


@pytest.mark.parametrize(
    "changes",
    [
        {"todayDate": "invalid"},
        {"tomorrowDate": "2026-08-10"},
        {"tomorrowTides": [{"@hora": "invalid", "@idTipoMarea": "1"}]},
    ],
)
async def test_invalid_new_forecast_fields_are_rejected(hass, changes):
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    with patch.object(
        hass,
        "async_add_executor_job",
        AsyncMock(return_value={**VALID_RESPONSE, **changes}),
    ):
        with pytest.raises(UpdateFailed, match="invalid"):
            await coordinator._async_update_data()

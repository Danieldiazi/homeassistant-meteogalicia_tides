"""Diagnostics tests."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteogalicia_tides.const import (
    CONF_ID_PORT,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.meteogalicia_tides.coordinator import (
    MeteoGaliciaTidesCoordinator,
)
from custom_components.meteogalicia_tides.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .test_coordinator_ha import VALID_RESPONSE


async def test_diagnostics_are_useful_and_do_not_expose_coordinates(hass):
    """Diagnostics contain support data but omit the API coordinates."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ID_PORT: "1"},
        options={CONF_SCAN_INTERVAL: 1800},
    )
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    coordinator.data = VALID_RESPONSE
    entry.runtime_data = coordinator

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"] == {
        "port_id": "1",
        "scan_interval_seconds": 1800,
    }
    assert result["coordinator"]["last_update_success"] is True
    assert result["coordinator"]["consecutive_failures"] == 0
    assert result["coordinator"]["effective_update_interval_seconds"] == 30
    assert result["library"]["meteogalicia_api_version"] == "0.1.2"
    assert result["response"]["today_tide_count"] == 1
    assert result["response"]["has_tomorrow_tide"] is True
    assert "pointGeoRSS" not in str(result)

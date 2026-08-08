"""Diagnostics for MeteoGalicia Tides."""

from typing import Any

from homeassistant.core import HomeAssistant

from . import MeteoGaliciaTidesConfigEntry
from .const import (
    CONF_ID_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MeteoGaliciaTidesConfigEntry
) -> dict[str, Any]:
    """Return non-sensitive diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    response = data if isinstance(data, dict) else {}
    today_tides = response.get("todayTides")

    return {
        "entry": {
            "port_id": entry.data[CONF_ID_PORT],
            "scan_interval_seconds": entry.options.get(
                CONF_SCAN_INTERVAL,
                entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                str(coordinator.last_exception)
                if coordinator.last_exception is not None
                else None
            ),
            "response_type": type(data).__name__,
        },
        "response": {
            "port_name": response.get("portName"),
            "forecast_date": response.get("date"),
            "today_tide_count": (
                len(today_tides) if isinstance(today_tides, list) else 0
            ),
            "has_tomorrow_tide": isinstance(
                response.get("tomorrowFirstTide"), dict
            ),
        },
    }

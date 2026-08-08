"""The MeteoGalicia Tides integration."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ID_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import MeteoGaliciaTidesCoordinator

type MeteoGaliciaTidesConfigEntry = ConfigEntry[MeteoGaliciaTidesCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: MeteoGaliciaTidesConfigEntry
) -> bool:
    """Set up MeteoGalicia Tides from a config entry."""
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    coordinator = MeteoGaliciaTidesCoordinator(
        hass,
        entry.data[CONF_ID_PORT],
        timedelta(seconds=int(scan_interval)),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MeteoGaliciaTidesConfigEntry
) -> bool:
    """Unload a MeteoGalicia Tides config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant, entry: MeteoGaliciaTidesConfigEntry
) -> None:
    """Reload an entry after its options change."""
    await hass.config_entries.async_reload(entry.entry_id)

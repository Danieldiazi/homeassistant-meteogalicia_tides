"""The MeteoGalicia Tides integration."""

import asyncio
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_ID_PORT,
    CONF_RESET_ENTITIES,
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
    try:
        await coordinator.async_config_entry_first_refresh()
        if entry.data.get(CONF_RESET_ENTITIES):
            entity_registry = er.async_get(hass)
            for entity in er.async_entries_for_config_entry(
                entity_registry, entry.entry_id
            ):
                entity_registry.async_remove(entity.entity_id)
            device_registry = dr.async_get(hass)
            for device in dr.async_entries_for_config_entry(
                device_registry, entry.entry_id
            ):
                if hasattr(device, "config_entry_id"):
                    device_registry.async_remove_device(device.id)
                else:
                    device_registry.async_update_device(
                        device.id, remove_config_entry_id=entry.entry_id
                    )
            data = dict(entry.data)
            data.pop(CONF_RESET_ENTITIES)
            hass.config_entries.async_update_entry(entry, data=data)
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception, asyncio.CancelledError:
        await coordinator.async_shutdown()
        raise
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MeteoGaliciaTidesConfigEntry
) -> bool:
    """Unload a MeteoGalicia Tides config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded

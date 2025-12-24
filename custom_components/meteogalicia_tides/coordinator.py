"""Coordinator for the MeteoGalicia_Tides integration."""
from datetime import timedelta
import logging

import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from meteogalicia_api.interface import MeteoGalicia

from . import const

_LOGGER = logging.getLogger(__name__)

_DEFAULT_UPDATE_INTERVAL = timedelta(seconds=30)


class MeteoGaliciaTidesCoordinator(DataUpdateCoordinator):
    """Class to manage fetching MeteoGalicia tide data."""

    def __init__(self, hass, id_port):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{const.DOMAIN}_{id_port}",
            update_interval=_DEFAULT_UPDATE_INTERVAL,
        )
        self.id_port = id_port

    async def _async_update_data(self):
        """Fetch data from the MeteoGalicia API."""
        try:
            async with async_timeout.timeout(const.TIMEOUT):
                return await self.hass.async_add_executor_job(
                    _get_forecast_tide_data_from_api, self.id_port
                )
        except Exception as err:
            raise UpdateFailed(err) from err


def _get_forecast_tide_data_from_api(id_port):
    """Call MeteoGalicia API to get tide forecast data."""
    meteogalicia_api = MeteoGalicia()
    return meteogalicia_api.get_forecast_tide(id_port)

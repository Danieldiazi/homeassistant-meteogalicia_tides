"""Coordinator for the MeteoGalicia_Tides integration."""
import asyncio
from collections.abc import Mapping
from datetime import timedelta
import logging

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
            async with asyncio.timeout(const.TIMEOUT):
                response = await self.hass.async_add_executor_job(
                    _get_forecast_tide_data_from_api, self.id_port
                )
        except TimeoutError as err:
            raise UpdateFailed(
                f"MeteoGalicia request timed out after {const.TIMEOUT} seconds"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected MeteoGalicia API error: {err}") from err

        if response is None:
            raise UpdateFailed("MeteoGalicia API returned no data")
        if not _is_valid_response(response):
            raise UpdateFailed("MeteoGalicia API returned an invalid response")
        return response


def _get_forecast_tide_data_from_api(id_port):
    """Call MeteoGalicia API to get tide forecast data."""
    meteogalicia_api = MeteoGalicia()
    return meteogalicia_api.get_forecast_tide(id_port)


def _is_valid_response(response):
    """Validate the stable response structure used by the entities."""
    if not isinstance(response, Mapping) or not response.get("pointGeoRSS"):
        return False

    today_tides = response.get("todayTides")
    tomorrow_first_tide = response.get("tomorrowFirstTide")
    if not isinstance(today_tides, list):
        return False
    if tomorrow_first_tide is not None and not isinstance(
        tomorrow_first_tide, Mapping
    ):
        return False
    return all(isinstance(tide, Mapping) for tide in today_tides)

"""Coordinator for the MeteoGalicia_Tides integration."""
import asyncio
import logging
from collections.abc import Mapping
from datetime import timedelta
from time import monotonic

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from meteogalicia_api.interface import MeteoGalicia

from . import const

_LOGGER = logging.getLogger(__name__)

class MeteoGaliciaTidesCoordinator(DataUpdateCoordinator):
    """Class to manage fetching MeteoGalicia tide data."""

    def __init__(self, hass, id_port, update_interval=None):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{const.DOMAIN}_{id_port}",
            update_interval=update_interval or const.DEFAULT_UPDATE_INTERVAL,
        )
        self.id_port = id_port
        self.configured_update_interval = (
            update_interval or const.DEFAULT_UPDATE_INTERVAL
        )
        self.consecutive_failures = 0
        self.last_attempt = None
        self.last_success = None
        self.last_request_duration = None
        self.last_failure_reason = None

    async def _async_update_data(self):
        """Fetch data from the MeteoGalicia API."""
        self.last_attempt = dt_util.utcnow()
        started = monotonic()
        try:
            async with asyncio.timeout(const.TIMEOUT):
                response = await self.hass.async_add_executor_job(
                    _get_forecast_tide_data_from_api, self.id_port
                )
        except TimeoutError as err:
            message = (
                f"MeteoGalicia request timed out after {const.TIMEOUT} seconds"
            )
            self._record_failure(message, started)
            raise UpdateFailed(message) from err
        except Exception as err:
            message = f"Unexpected MeteoGalicia API error: {err}"
            self._record_failure(message, started)
            raise UpdateFailed(message) from err

        if response is None:
            message = "MeteoGalicia API returned no data"
            self._record_failure(message, started)
            raise UpdateFailed(message)
        if not _is_valid_response(response):
            message = "MeteoGalicia API returned an invalid response"
            self._record_failure(message, started)
            raise UpdateFailed(message)
        self._record_success(started)
        return response

    def _record_success(self, started):
        """Record a successful request and restore the configured cadence."""
        self.last_request_duration = monotonic() - started
        self.last_success = dt_util.utcnow()
        self.last_failure_reason = None
        self.consecutive_failures = 0
        self.update_interval = self.configured_update_interval

    def _record_failure(self, reason, started):
        """Record a failure and progressively reduce request frequency."""
        self.last_request_duration = monotonic() - started
        self.last_failure_reason = reason
        self.consecutive_failures += 1
        multiplier = min(
            2**self.consecutive_failures, const.MAX_BACKOFF_MULTIPLIER
        )
        self.update_interval = timedelta(
            seconds=min(
                self.configured_update_interval.total_seconds() * multiplier,
                const.MAX_SCAN_INTERVAL,
            )
        )


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
    tides = [*today_tides]
    if tomorrow_first_tide is not None:
        tides.append(tomorrow_first_tide)
    return bool(tides) and all(_is_valid_tide(tide) for tide in tides)


def _is_valid_tide(tide):
    """Return whether a tide has the fields required by every entity."""
    if not isinstance(tide, Mapping):
        return False
    tide_time = tide.get(const.HORA_FIELD)
    if not isinstance(tide_time, str):
        return False
    try:
        hour, minute = (int(value) for value in tide_time.split(":", 1))
        int(tide[const.ID_TIPO_MAREA_FIELD])
    except (KeyError, TypeError, ValueError):
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59

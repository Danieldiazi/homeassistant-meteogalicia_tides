"""Coordinator for the MeteoGalicia_Tides integration."""

import asyncio
import logging
from collections.abc import Mapping
from datetime import datetime, timedelta
from threading import Lock
from time import monotonic

import requests
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from meteogalicia_api.interface import MeteoGalicia

from . import const
from .tide import TIDE_TIME_ZONE, upcoming_tides, with_forecast_dates

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
        self._unsub_transition = None
        self._transition_listeners = 0
        self._session = requests.Session()
        self._client = MeteoGalicia(session=self._session, timeout=const.TIMEOUT)
        self._session_lock = Lock()
        self._closed = False

    @callback
    def async_add_listener(self, update_callback, context=None):
        """Share one local transition timer across all port entities."""
        remove = super().async_add_listener(update_callback, context)
        self._transition_listeners += 1
        self._schedule_transition(self.data)
        removed = False

        @callback
        def remove_listener():
            nonlocal removed
            if removed:
                return
            removed = True
            remove()
            self._transition_listeners -= 1
            if not self._transition_listeners:
                self._cancel_transition()

        return remove_listener

    @callback
    def _cancel_transition(self):
        if self._unsub_transition is not None:
            self._unsub_transition()
            self._unsub_transition = None

    @callback
    def _schedule_transition(self, data):
        self._cancel_transition()
        if not self._transition_listeners or not data:
            return
        now = dt_util.now(TIDE_TIME_ZONE)
        midnight = datetime.combine(
            now.date() + timedelta(days=1),
            datetime.min.time(),
            tzinfo=TIDE_TIME_ZONE,
        )
        candidates = upcoming_tides(data, now)
        transition = min(midnight, candidates[0][1]) if candidates else midnight
        if data["todayDate"] < now.date().isoformat() or not candidates:
            # The published client may still return yesterday's window around
            # local midnight on a UTC host. Retry until a fresh window arrives,
            # even when the configured network interval is a whole day.
            transition = min(transition, now + timedelta(minutes=15))
        self._unsub_transition = async_track_point_in_time(
            self.hass, self._async_time_transition, transition
        )

    @callback
    def _async_time_transition(self, _now):
        """Publish time-based changes without resetting the polling cadence."""
        self._unsub_transition = None
        self.async_update_listeners()
        self._schedule_transition(self.data)
        now = dt_util.now(TIDE_TIME_ZONE)
        if self.data and (
            self.data["todayDate"] < now.date().isoformat()
            or not upcoming_tides(self.data, now)
        ):
            self.hass.async_create_task(self.async_request_refresh())

    async def async_shutdown(self):
        """Stop timers and close the session after any in-flight request finishes."""
        if self._closed:
            return
        self._closed = True
        self._cancel_transition()
        await super().async_shutdown()
        await self.hass.async_add_executor_job(self._close_session)

    def _close_session(self):
        with self._session_lock:
            self._session.close()

    def _get_forecast(self):
        # A timed-out executor job can keep running. Serialize requests and
        # closing so the requests.Session is never used by two threads at once.
        with self._session_lock:
            if self._closed:
                raise RuntimeError("MeteoGalicia coordinator has been shut down")
            return self._client.get_forecast_tide(self.id_port)

    async def _async_update_data(self):
        """Fetch data from the MeteoGalicia API."""
        self.last_attempt = dt_util.utcnow()
        started = monotonic()
        try:
            async with asyncio.timeout(const.TIMEOUT):
                response = await self.hass.async_add_executor_job(self._get_forecast)
        except TimeoutError as err:
            message = f"MeteoGalicia request timed out after {const.TIMEOUT} seconds"
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
        try:
            response = with_forecast_dates(response)
        except (KeyError, TypeError, ValueError) as err:
            message = "MeteoGalicia API returned an invalid forecast date"
            self._record_failure(message, started)
            raise UpdateFailed(message) from err
        self._record_success(started)
        self._schedule_transition(response)
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
        multiplier = min(2**self.consecutive_failures, const.MAX_BACKOFF_MULTIPLIER)
        self.update_interval = timedelta(
            seconds=min(
                self.configured_update_interval.total_seconds() * multiplier,
                const.MAX_SCAN_INTERVAL,
            )
        )


def _get_forecast_tide_data_from_api(id_port):
    """Call MeteoGalicia API to get tide forecast data."""
    with requests.Session() as session:
        return MeteoGalicia(session=session, timeout=const.TIMEOUT).get_forecast_tide(
            id_port
        )


def _is_valid_response(response):
    """Validate the stable response structure used by the entities."""
    if not isinstance(response, Mapping) or not response.get("pointGeoRSS"):
        return False

    today_tides = response.get("todayTides")
    tomorrow_first_tide = response.get("tomorrowFirstTide")
    if not isinstance(today_tides, list):
        return False
    if tomorrow_first_tide is not None and not isinstance(tomorrow_first_tide, Mapping):
        return False
    tides = [*today_tides]
    if "tomorrowTides" in response:
        tomorrow_tides = response["tomorrowTides"]
        if not isinstance(tomorrow_tides, list):
            return False
        tides.extend(tomorrow_tides)
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
    except KeyError, TypeError, ValueError:
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59

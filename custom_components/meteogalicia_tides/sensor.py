"""The Sensor module for MeteoGalicia_Tides integration."""
import sys
import logging
import async_timeout
import voluptuous as vol
from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import __version__, TEMP_CELSIUS, PERCENTAGE
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from . import const
from homeassistant.util import dt
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)


from meteogalicia_api.interface import MeteoGalicia

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by MeteoGalicia"

# Obtaining config from configuration.yaml
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(const.CONF_ID_PORT): cv.string, }

)


async def async_setup_platform(
    hass, config, add_entities, discovery_info=None
):  # pylint: disable=missing-docstring, unused-argument
    """Run async_setup_platform"""

    session = async_create_clientsession(hass)
    if config.get(const.CONF_ID_PORT, ""):
        id_port = config[const.CONF_ID_PORT]
        if not id_port.isnumeric():
            _LOGGER.critical(
                "Configured (YAML) 'id_port '%s' is not valid", id_port
            )
            return False
        else:
            try:
                async with async_timeout.timeout(const.TIMEOUT):
                    await get_forecast_tide_data(hass, id_port)
            except Exception as exception:
                _LOGGER.warning("[%s] %s", sys.exc_info()
                                [0].__name__, exception)
                raise PlatformNotReady

            add_entities(
                [
                    MeteoGaliciaForecastTide(
                        id_port, session, hass
                    )
                ],
                True,
            )
            _LOGGER.info(
                "Added tide forecast sensor for port with id '%s'",  id_port)


async def get_forecast_tide_data(hass, id_port):
    """Poll weather data from MeteoGalicia API."""

    data = await hass.async_add_executor_job(_get_forecast_tide_data_from_api, id_port)
    return data


def _get_forecast_tide_data_from_api(id_port):
    """Call meteogalicia api in order to get obsertation data"""
    meteogalicia_api = MeteoGalicia()
    data = meteogalicia_api.get_forecast_tide(id_port)
    return data


class MeteoGaliciaForecastTide(
    SensorEntity
):  # pylint: disable=missing-docstring
    """Sensor class."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, idc, session, hass):
        self.id = idc
        self.session = session
        self._state = 0
        self.connected = True
        self.exception = None
        self._attr = {}
        self.hass = hass

    async def async_update(self) -> None:
        """Run async update ."""
        information = []
        connected = False
        try:
            self._name = self.id
            async with async_timeout.timeout(const.TIMEOUT):

                response = await get_forecast_tide_data(self.hass, self.id)

                if response is None:
                    self._state = None
                    _LOGGER.warning(
                        "[%s] Possible API  connection  problem. Currently unable to download data from MeteoGalicia - HTTP status code %s",
                        self.id,
                        response.status,
                    )
                else:

                    # _LOGGER.info("Test '%s' : '%s'",   self.id, data.get("predConcello")["listaPredDiaConcello"],     )
                    if response.get("pointGeoRSS") is not None:
                        item = response
                        state = "down"

                        self._name = item.get("portName")

                        self._attr = {
                            "information": information,
                            "integration": "meteogalicia_tides",
                            "title": item.get("portName"),
                            "date": item.get("date"),
                            "id": self.id,
                        }
                        lista_mareas = item.get("todayTides")

                        marea = getNextTide (lista_mareas,item.get("tomorrowFirstTide") )

                        self._attr["state"] = marea.get("@estado")
                        self._attr["height"] = marea.get("@altura")
                        self._attr["hour"] = marea.get(const.HORA_FIELD)
                        if int(marea.get("@idTipoMarea")) == 0:
                            state = "Low tide at " + marea.get(const.HORA_FIELD)
                        else:
                            state = "High tide at " + marea.get(const.HORA_FIELD)

                        self._state = state

        except Exception:  # pylint: disable=broad-except
            self.exception = sys.exc_info()  # [0].__name__
            connected = False
        else:
            connected = True
        finally:
            # Handle connection messages here.
            if self.connected:
                if not connected:
                    self._state = None
                    _LOGGER.warning(
                        "[%s] Couldn't update sensor (%s)",
                        self.id,
                        self.exception,
                    )

            elif not self.connected:
                if connected:
                    _LOGGER.info("[%s] Update of sensor completed", self.id)
                else:
                    self._state = None
                    _LOGGER.warning(
                        "[%s] Still no update available (%s)", self.id, self.exception
                    )

            self.connected = connected

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self._name} - Forecast Tides"

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this sensor."""
        return f"{const.INTEGRATION_NAME.lower()}_forecast_tides_id_{self.id}".replace(
            ",", ""
        )

    @property
    def icon(self):
        """Return icon."""
        return "mdi:waves"

    @property
    def extra_state_attributes(self):
        """Return attributes."""
        return self._attr

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state


def getNextTide(lista_mareas, tomorrow_next_tide):

    marea = None

    id_next_tide = 0

    for marea in lista_mareas:

        hour = int(dt.now().strftime("%H"))
        minute = int(dt.now().strftime("%M"))
        hour_tide = marea.get(const.HORA_FIELD).split(":")[0]
        minute_tide = marea.get(const.HORA_FIELD).split(":")[1]
        if (hour > int(hour_tide)) or (hour == int(hour_tide) and (minute >= int(minute_tide))):
            id_next_tide = int(marea.get("@id")) + 1

    if (id_next_tide >= len(lista_mareas)):
        marea = tomorrow_next_tide
    else:
        marea = lista_mareas[id_next_tide]
    return marea
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
    { vol.Required(const.CONF_ID_PORT): cv.string,}
    
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
                    response = await get_forecast_tide_data(hass, id_port)
            except Exception as exception:
                _LOGGER.warning("[%s] %s", sys.exc_info()[0].__name__, exception)
                raise PlatformNotReady

            add_entities(
            [
                MeteoGaliciaForecastTide(
                     id_port, session, hass
                )
            ],
            True,
                )
            _LOGGER.info("Added tide forecast sensor for port with id '%s'",  id_port)





async def get_forecast_tide_data(hass, idP):
    """Poll weather data from MeteoGalicia API."""

    data = await hass.async_add_executor_job(_get_forecast_tide_data_from_api, idP)
    return data


def _get_forecast_tide_data_from_api(idP):
    """Call meteogalicia api in order to get obsertation data"""
    meteogalicia_api = MeteoGalicia()
    data = meteogalicia_api.get_forecast_tide(idP)
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
                        listaMareas = item.get("todayTides")
                        
                        if int(item.get("todayTides")[0]['@idTipoMarea']) ==1:
                            state = "up"
                        else:
                            state ="down" 

                        
                        for marea in listaMareas:
                            self._attr["marea_"+marea.get("@id")+"_estado"] = marea.get("@estado")
                            self._attr["marea_"+marea.get("@id")+"_hora"] = marea.get("@hora")
                            self._attr["marea_"+marea.get("@id")+"_altura"] = marea.get("@altura")
                            hour = int(dt.now().strftime("%H"))
                            minute = int(dt.now().strftime("%M"))
                            hourTide = marea.get("@hora").split(":")[0]
                            minuteTide = marea.get("@hora").split(":")[1]
                            if (hour > int(hourTide)) or (hour == int(hourTide) and (minute >=int(minuteTide))):
                                if int(marea.get("@idTipoMarea")) == 1:
                                 state = "down"
                                else:
                                    state ="up"
                                
                        

                        self._state = state
                        

        except Exception:  # pylint: disable=broad-except
            self.exception = sys.exc_info() #[0].__name__
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



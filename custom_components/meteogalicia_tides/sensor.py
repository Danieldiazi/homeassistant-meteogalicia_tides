"""The Sensor module for MeteoGalicia_Tides integration."""
import logging
import voluptuous as vol
from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from . import const
from homeassistant.util import dt
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MeteoGaliciaTidesCoordinator

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

    if config.get(const.CONF_ID_PORT, ""):
        id_port = config[const.CONF_ID_PORT]
        if not id_port.isnumeric():
            _LOGGER.critical(
                "Configured (YAML) 'id_port '%s' is not valid", id_port
            )
            return False
        else:
            coordinator = MeteoGaliciaTidesCoordinator(hass, id_port)
            await coordinator.async_refresh()
            if not coordinator.last_update_success:
                raise PlatformNotReady

            add_entities([MeteoGaliciaForecastTide(id_port, coordinator)])
            _LOGGER.info(
                "Added tide forecast sensor for port with id '%s'",  id_port)


class MeteoGaliciaForecastTide(
    CoordinatorEntity, SensorEntity
):  # pylint: disable=missing-docstring
    """Sensor class."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, idc, coordinator):
        super().__init__(coordinator)
        self.id = idc
        self._state = None
        self._attr = {}
        self._name = str(idc)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        parsed = self._parse_response(self.coordinator.data)
        if not parsed:
            self._state = None
            self._attr = {}
        else:
            self._state, self._attr = parsed
        self.async_write_ha_state()

    def _parse_response(self, response):
        if response is None:
            self._state = None
            _LOGGER.warning(
                "[%s] Possible API connection problem. Currently unable to download data from MeteoGalicia",
                self.id,
            )
            return None

        if response.get("pointGeoRSS") is None:
            self._state = None
            _LOGGER.warning("[%s] Missing tide data from MeteoGalicia", self.id)
            return None

        item = response
        self._name = item.get("portName")

        lista_mareas = item.get("todayTides")
        marea = get_next_tide(
            lista_mareas, item.get("tomorrowFirstTide")
        )
        if not marea:
            self._state = None
            _LOGGER.warning(
                "[%s] No tide data available from MeteoGalicia",
                self.id,
            )
            return None

        if not marea.get(const.HORA_FIELD):
            self._state = None
            _LOGGER.warning(
                "[%s] Missing tide hour data from MeteoGalicia",
                self.id,
            )
            return None

        if marea.get(const.ID_TIPO_MAREA_FIELD) is None:
            self._state = None
            _LOGGER.warning(
                "[%s] Missing tide type data from MeteoGalicia",
                self.id,
            )
            return None

        attrs = self._build_attributes(item, marea)
        state = get_state_from_tide(marea)
        if state is None:
            self._state = None
            _LOGGER.warning(
                "[%s] Invalid tide data from MeteoGalicia",
                self.id,
            )
            return None
        return state, attrs

    def _build_attributes(self, item, marea):
        attrs = {
            "information": [],
            "integration": "meteogalicia_tides",
            "title": item.get("portName"),
            "date": item.get("date"),
            "id": self.id,
            "state": marea.get(const.ESTADO_FIELD),
            "height": marea.get(const.ALTURA_FIELD),
            "hour": marea.get(const.HORA_FIELD),
        }
        return attrs

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


def get_next_tide(lista_mareas, tomorrow_next_tide):

    if not lista_mareas:
        return tomorrow_next_tide

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


def get_state_from_tide(marea):
    if not marea:
        return None

    tide_type = marea.get(const.ID_TIPO_MAREA_FIELD)
    tide_time = marea.get(const.HORA_FIELD)
    if tide_type is None or not tide_time:
        return None

    try:
        tide_type_int = int(tide_type)
    except (TypeError, ValueError):
        return None

    if tide_type_int == 0:
        state = f"Low tide at {tide_time}"
    else:
        state = f"High tide at {tide_time}"
    return state

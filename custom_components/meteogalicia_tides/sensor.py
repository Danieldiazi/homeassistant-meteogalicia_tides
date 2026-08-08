"""Sensor platform for the MeteoGalicia Tides integration."""

from datetime import datetime, timedelta
import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt

from . import const
from .coordinator import MeteoGaliciaTidesCoordinator
from .tide import get_next_tide, get_next_tide_with_day, get_state_from_tide

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by MeteoGalicia"

# Obtaining config from configuration.yaml
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(const.CONF_ID_PORT): cv.string}
)

NEXT_TIDE_TIME_DESCRIPTION = SensorEntityDescription(
    key="next_tide_time",
    translation_key="next_tide_time",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_registry_enabled_default=False,
)
TIDE_TYPE_DESCRIPTION = SensorEntityDescription(
    key="next_tide_type",
    translation_key="next_tide_type",
    entity_registry_enabled_default=False,
)
TIDE_HEIGHT_DESCRIPTION = SensorEntityDescription(
    key="next_tide_height",
    translation_key="next_tide_height",
    native_unit_of_measurement=UnitOfLength.METERS,
    entity_registry_enabled_default=False,
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

            add_entities(_create_entities(id_port, coordinator))
            _LOGGER.info(
                "Added tide forecast sensor for port with id '%s'",  id_port)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = hass.data[const.DOMAIN][entry.entry_id]
    async_add_entities(_create_entities(entry.data[const.CONF_ID_PORT], coordinator))


def _create_entities(id_port, coordinator):
    """Create the legacy sensor and additional disabled-by-default sensors."""
    return [
        MeteoGaliciaForecastTide(id_port, coordinator),
        MeteoGaliciaTideTimeSensor(id_port, coordinator, NEXT_TIDE_TIME_DESCRIPTION),
        MeteoGaliciaTideTypeSensor(id_port, coordinator, TIDE_TYPE_DESCRIPTION),
        MeteoGaliciaTideHeightSensor(id_port, coordinator, TIDE_HEIGHT_DESCRIPTION),
    ]


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
        self._update_from_response(self.coordinator.data)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_response(self.coordinator.data)
        self.async_write_ha_state()

    def _update_from_response(self, response) -> None:
        """Update cached legacy state and attributes."""
        parsed = self._parse_response(response)
        if not parsed:
            self._state = None
            self._attr = {}
        else:
            self._state, self._attr = parsed

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
            lista_mareas, item.get("tomorrowFirstTide"), dt.now()
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

    @property
    def device_info(self) -> DeviceInfo:
        """Return information grouping entities for this port."""
        return _device_info(self.id, self._name)


class MeteoGaliciaTideSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for structured tide sensors."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, id_port, coordinator, description):
        super().__init__(coordinator)
        self.id_port = id_port
        self.entity_description = description
        self._attr_unique_id = (
            f"{const.INTEGRATION_NAME.lower()}_{description.key}_id_{id_port}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return information grouping entities for this port."""
        data = self.coordinator.data or {}
        return _device_info(
            self.id_port, data.get("portName") or str(self.id_port)
        )

    def _selection(self):
        data = self.coordinator.data or {}
        return get_next_tide_with_day(
            data.get("todayTides"), data.get("tomorrowFirstTide"), dt.now()
        )


class MeteoGaliciaTideTimeSensor(MeteoGaliciaTideSensorBase):
    """Timestamp of the next tide."""

    @property
    def native_value(self) -> datetime | None:
        """Return the local date and time of the next tide."""
        tide, is_tomorrow = self._selection()
        if not tide or not isinstance(tide.get(const.HORA_FIELD), str):
            return None
        try:
            hour, minute = (
                int(value) for value in tide[const.HORA_FIELD].split(":", 1)
            )
            current = dt.now()
            tide_date = current.date() + timedelta(days=int(is_tomorrow))
            return datetime.combine(
                tide_date, datetime.min.time(), tzinfo=current.tzinfo
            ).replace(hour=hour, minute=minute)
        except (TypeError, ValueError):
            return None


class MeteoGaliciaTideTypeSensor(MeteoGaliciaTideSensorBase):
    """Type of the next tide."""

    @property
    def native_value(self) -> str | None:
        """Return high or low for the next tide."""
        tide, _ = self._selection()
        if not tide:
            return None
        try:
            return (
                "low"
                if int(tide.get(const.ID_TIPO_MAREA_FIELD)) == 0
                else "high"
            )
        except (TypeError, ValueError):
            return None


class MeteoGaliciaTideHeightSensor(MeteoGaliciaTideSensorBase):
    """Height of the next tide."""

    @property
    def native_value(self) -> float | None:
        """Return the next tide height in metres."""
        tide, _ = self._selection()
        if not tide:
            return None
        try:
            return float(str(tide.get(const.ALTURA_FIELD)).replace(",", "."))
        except (TypeError, ValueError):
            return None


def _device_info(id_port, port_name) -> DeviceInfo:
    """Build stable device information for a port."""
    return DeviceInfo(
        identifiers={(const.DOMAIN, str(id_port))},
        manufacturer="MeteoGalicia",
        name=str(port_name),
        model="Tide forecast",
    )

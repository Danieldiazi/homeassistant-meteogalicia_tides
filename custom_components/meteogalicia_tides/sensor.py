"""Sensor platform for the MeteoGalicia Tides integration."""

import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt

from . import const
from .tide import TIDE_TIME_ZONE, get_state_from_tide, tides_on_day, upcoming_tides

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by MeteoGalicia"

# Obtaining config from configuration.yaml
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(const.CONF_ID_PORT): cv.string})

NEXT_TIDE_TIME_DESCRIPTION = SensorEntityDescription(
    key="next_tide_time",
    translation_key="next_tide_time",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_registry_enabled_default=False,
)
TIDE_TYPE_DESCRIPTION = SensorEntityDescription(
    key="next_tide_type",
    translation_key="next_tide_type",
    device_class=SensorDeviceClass.ENUM,
    options=["high", "low"],
    entity_registry_enabled_default=False,
)
TIDE_HEIGHT_DESCRIPTION = SensorEntityDescription(
    key="next_tide_height",
    translation_key="next_tide_height",
    native_unit_of_measurement=UnitOfLength.METERS,
    entity_registry_enabled_default=False,
)
NEXT_HIGH_TIDE_DESCRIPTION = SensorEntityDescription(
    key="next_high_tide",
    translation_key="next_high_tide",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_registry_enabled_default=False,
)
NEXT_LOW_TIDE_DESCRIPTION = SensorEntityDescription(
    key="next_low_tide",
    translation_key="next_low_tide",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_registry_enabled_default=False,
)
SECOND_NEXT_TIDE_DESCRIPTION = SensorEntityDescription(
    key="second_next_tide",
    translation_key="second_next_tide",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_registry_enabled_default=False,
)
TODAY_TIDE_COUNT_DESCRIPTION = SensorEntityDescription(
    key="today_tide_count",
    translation_key="today_tide_count",
    icon="mdi:counter",
    entity_registry_enabled_default=False,
)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):  # pylint: disable=missing-docstring, unused-argument
    """Import legacy YAML configuration into a config entry."""
    import_data = {const.CONF_ID_PORT: config[const.CONF_ID_PORT]}
    if scan_interval := config.get(const.CONF_SCAN_INTERVAL):
        import_data[const.CONF_SCAN_INTERVAL] = int(
            scan_interval.total_seconds()
            if isinstance(scan_interval, timedelta)
            else scan_interval
        )
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN,
        context={"source": SOURCE_IMPORT},
        data=import_data,
    )
    if result["type"] in {"create_entry", "abort"}:
        ir.async_create_issue(
            hass,
            const.DOMAIN,
            f"remove_yaml_{import_data[const.CONF_ID_PORT]}",
            is_fixable=False,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="remove_yaml",
            translation_placeholders={"port": str(import_data[const.CONF_ID_PORT])},
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(_create_entities(entry.data[const.CONF_ID_PORT], coordinator))


def _create_entities(id_port, coordinator):
    """Create the legacy sensor and additional disabled-by-default sensors."""
    return [
        MeteoGaliciaForecastTide(id_port, coordinator),
        MeteoGaliciaTideTimeSensor(id_port, coordinator, NEXT_TIDE_TIME_DESCRIPTION),
        MeteoGaliciaTideTypeSensor(id_port, coordinator, TIDE_TYPE_DESCRIPTION),
        MeteoGaliciaTideHeightSensor(id_port, coordinator, TIDE_HEIGHT_DESCRIPTION),
        MeteoGaliciaFilteredTideTimeSensor(
            id_port, coordinator, NEXT_HIGH_TIDE_DESCRIPTION, tide_type=1
        ),
        MeteoGaliciaFilteredTideTimeSensor(
            id_port, coordinator, NEXT_LOW_TIDE_DESCRIPTION, tide_type=0
        ),
        MeteoGaliciaFilteredTideTimeSensor(
            id_port, coordinator, SECOND_NEXT_TIDE_DESCRIPTION, position=1
        ),
        MeteoGaliciaTodayTideCountSensor(
            id_port, coordinator, TODAY_TIDE_COUNT_DESCRIPTION
        ),
    ]


class MeteoGaliciaForecastTide(CoordinatorEntity, SensorEntity):
    """Preserve the installed entity ID and legacy state text."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, idc, coordinator):
        super().__init__(coordinator)
        self.id = idc
        self._name = (coordinator.data or {}).get("portName") or str(idc)

    def _selection(self):
        candidates = upcoming_tides(self.coordinator.data or {}, dt.now(TIDE_TIME_ZONE))
        return candidates[0] if candidates else (None, None)

    @property
    def name(self):
        return f"{self._name} - Forecast Tides"

    @property
    def unique_id(self):
        return f"{const.INTEGRATION_NAME.lower()}_forecast_tides_id_{self.id}".replace(
            ",", ""
        )

    @property
    def icon(self):
        return "mdi:waves"

    @property
    def native_value(self):
        tide, _timestamp = self._selection()
        return get_state_from_tide(tide)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        tide, timestamp = self._selection()
        return {
            "information": [],
            "integration": "meteogalicia_tides",
            "title": data.get("portName"),
            "date": data.get("date"),
            "id": self.id,
            "state": tide.get(const.ESTADO_FIELD) if tide else None,
            "height": tide.get(const.ALTURA_FIELD) if tide else None,
            "hour": tide.get(const.HORA_FIELD) if tide else None,
            "next_tide_time": timestamp.isoformat() if timestamp else None,
        }

    @property
    def device_info(self):
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
    def device_info(self):
        data = self.coordinator.data or {}
        return _device_info(self.id_port, data.get("portName") or str(self.id_port))

    def _selection(self):
        candidates = upcoming_tides(self.coordinator.data or {}, dt.now(TIDE_TIME_ZONE))
        return candidates[0] if candidates else (None, None)


class MeteoGaliciaTideTimeSensor(MeteoGaliciaTideSensorBase):
    """Timestamp of the next tide."""

    @property
    def native_value(self):
        return self._selection()[1]


class MeteoGaliciaTideTypeSensor(MeteoGaliciaTideSensorBase):
    """Type of the next tide."""

    @property
    def native_value(self):
        tide, _timestamp = self._selection()
        tide_type = _tide_type(tide)
        return {0: "low", 1: "high"}.get(tide_type)


class MeteoGaliciaTideHeightSensor(MeteoGaliciaTideSensorBase):
    """Height of the next tide."""

    @property
    def native_value(self):
        tide, _timestamp = self._selection()
        if not tide:
            return None
        try:
            return float(str(tide.get(const.ALTURA_FIELD)).replace(",", "."))
        except TypeError, ValueError:
            return None


class MeteoGaliciaFilteredTideTimeSensor(MeteoGaliciaTideSensorBase):
    """Timestamp for a selected upcoming tide."""

    def __init__(self, id_port, coordinator, description, tide_type=None, position=0):
        super().__init__(id_port, coordinator, description)
        self.tide_type = tide_type
        self.position = position

    @property
    def native_value(self):
        candidates = upcoming_tides(self.coordinator.data or {}, dt.now(TIDE_TIME_ZONE))
        if self.tide_type is not None:
            candidates = [
                item for item in candidates if _tide_type(item[0]) == self.tide_type
            ]
        return candidates[self.position][1] if len(candidates) > self.position else None


class MeteoGaliciaTodayTideCountSensor(MeteoGaliciaTideSensorBase):
    """Number of tides for the actual current day."""

    @property
    def native_value(self):
        tides = tides_on_day(self.coordinator.data or {}, dt.now(TIDE_TIME_ZONE).date())
        return len(tides) if isinstance(tides, list) else None


def _tide_type(tide):
    """Return the numeric tide type or None."""
    try:
        return int(tide[const.ID_TIPO_MAREA_FIELD])
    except KeyError, TypeError, ValueError:
        return None


def _device_info(id_port, port_name) -> DeviceInfo:
    """Build stable device information for a port."""
    return DeviceInfo(
        identifiers={(const.DOMAIN, str(id_port))},
        manufacturer="MeteoGalicia",
        name=str(port_name),
        model="Tide forecast",
    )

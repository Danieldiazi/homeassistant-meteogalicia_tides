"""Home Assistant entity compatibility tests."""

from custom_components.meteogalicia_tides.coordinator import (
    MeteoGaliciaTidesCoordinator,
)
from custom_components.meteogalicia_tides.sensor import _create_entities

from .test_coordinator_ha import VALID_RESPONSE


def test_entity_identifiers_and_defaults_are_compatible(hass):
    """Keep the installed entity ID basis and opt-in structured sensors."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    coordinator.data = VALID_RESPONSE

    legacy, tide_time, tide_type, tide_height = _create_entities("1", coordinator)

    assert legacy.unique_id == "meteogalicia_tides_forecast_tides_id_1"
    assert legacy.name == "A Coruña - Forecast Tides"
    assert legacy.native_value in {"High tide at 23:59", "Low tide at 01:00"}
    assert tide_time.unique_id == "meteogalicia_tides_next_tide_time_id_1"
    assert tide_type.unique_id == "meteogalicia_tides_next_tide_type_id_1"
    assert tide_height.unique_id == "meteogalicia_tides_next_tide_height_id_1"
    assert tide_time.entity_description.entity_registry_enabled_default is False
    assert tide_type.entity_description.entity_registry_enabled_default is False
    assert tide_height.entity_description.entity_registry_enabled_default is False


def test_entities_become_unavailable_with_coordinator(hass):
    """A failed refresh marks all coordinator entities unavailable."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    coordinator.data = VALID_RESPONSE
    entities = _create_entities("1", coordinator)

    coordinator.last_update_success = False

    assert all(entity.available is False for entity in entities)

"""Home Assistant entity compatibility tests."""

from datetime import UTC, datetime
from unittest.mock import patch

from custom_components.meteogalicia_tides.coordinator import (
    MeteoGaliciaTidesCoordinator,
)
from custom_components.meteogalicia_tides.sensor import _create_entities

from .test_coordinator_ha import VALID_RESPONSE


def test_entity_identifiers_and_defaults_are_compatible(hass):
    """Keep the installed entity ID basis and opt-in structured sensors."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    coordinator.data = VALID_RESPONSE

    entities = _create_entities("1", coordinator)
    legacy, tide_time, tide_type, tide_height = entities[:4]

    assert legacy.unique_id == "meteogalicia_tides_forecast_tides_id_1"
    assert legacy.name == "A Coruña - Forecast Tides"
    assert legacy.native_value in {"High tide at 23:59", "Low tide at 01:00"}
    assert tide_time.unique_id == "meteogalicia_tides_next_tide_time_id_1"
    assert tide_type.unique_id == "meteogalicia_tides_next_tide_type_id_1"
    assert tide_height.unique_id == "meteogalicia_tides_next_tide_height_id_1"
    assert tide_type.native_value in {"high", "low"}
    assert isinstance(tide_height.native_value, float)
    assert tide_time.entity_description.entity_registry_enabled_default is False
    assert tide_type.entity_description.entity_registry_enabled_default is False
    assert tide_height.entity_description.entity_registry_enabled_default is False
    assert len(entities) == 8
    assert all(
        entity.entity_description.entity_registry_enabled_default is False
        for entity in entities[1:]
    )
    assert [entity.unique_id for entity in entities[4:]] == [
        "meteogalicia_tides_next_high_tide_id_1",
        "meteogalicia_tides_next_low_tide_id_1",
        "meteogalicia_tides_second_next_tide_id_1",
        "meteogalicia_tides_today_tide_count_id_1",
    ]


def test_entities_become_unavailable_with_coordinator(hass):
    """A failed refresh marks all coordinator entities unavailable."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    coordinator.data = VALID_RESPONSE
    entities = _create_entities("1", coordinator)

    coordinator.last_update_success = False

    assert all(entity.available is False for entity in entities)


def test_additional_tide_entities_expose_upcoming_forecast(hass):
    """Opt-in entities expose high, low, following, and daily count data."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    coordinator.data = VALID_RESPONSE

    with patch(
        "custom_components.meteogalicia_tides.sensor.dt.now",
        return_value=datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
    ):
        entities = _create_entities("1", coordinator)
        assert entities[4].native_value == datetime(
            2026, 8, 8, 23, 59, tzinfo=UTC
        )
        assert entities[5].native_value == datetime(
            2026, 8, 9, 1, 0, tzinfo=UTC
        )
        assert entities[6].native_value == datetime(
            2026, 8, 9, 1, 0, tzinfo=UTC
        )
        assert entities[7].native_value == 1

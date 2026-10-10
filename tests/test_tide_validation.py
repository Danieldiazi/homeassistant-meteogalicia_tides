"""Reject non-finite heights and unknown tide types before exposing states."""

from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from meteogalicia_api.errors import MeteoGaliciaHTTPError

from custom_components.meteogalicia_tides.coordinator import (
    MeteoGaliciaTidesCoordinator,
    _is_valid_tide,
)
from custom_components.meteogalicia_tides.sensor import _create_entities

from .test_coordinator_ha import VALID_RESPONSE


@pytest.mark.parametrize(
    "height", ["NaN", "Infinity", "-inf", float("nan"), "bad", None]
)
async def test_invalid_height_is_rejected(hass, height):
    response = deepcopy(VALID_RESPONSE)
    response["todayTides"][0]["@altura"] = height
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    try:
        with patch.object(
            hass, "async_add_executor_job", AsyncMock(return_value=response)
        ):
            with pytest.raises(UpdateFailed, match="invalid response"):
                await coordinator._async_update_data()
        assert coordinator.last_failure_kind == "invalid_response"
    finally:
        await coordinator.async_shutdown()


@pytest.mark.parametrize("tide_type", [2, -1, "9", "unknown", True, 1.5])
def test_unknown_type_is_rejected(tide_type):
    tide = dict(VALID_RESPONSE["todayTides"][0], **{"@idTipoMarea": tide_type})
    assert not _is_valid_tide(tide)


@pytest.mark.parametrize("height", ["0,8", "3.2", -0.1, 0])
def test_valid_heights_remain_supported(height):
    tide = dict(VALID_RESPONSE["todayTides"][0], **{"@altura": height})
    assert _is_valid_tide(tide)


async def test_tide_rate_limit_respects_retry_after(hass):
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    try:
        with patch.object(
            hass,
            "async_add_executor_job",
            AsyncMock(side_effect=MeteoGaliciaHTTPError(429, retry_after=3600)),
        ):
            with pytest.raises(UpdateFailed, match="429"):
                await coordinator._async_update_data()
        assert coordinator.last_failure_kind == "http"
        assert coordinator.update_interval.total_seconds() == 3600
    finally:
        await coordinator.async_shutdown()


async def test_publication_age_does_not_reset_on_success(hass, freezer):
    freezer.move_to("2026-08-08T00:02:00Z")
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    coordinator.data = deepcopy(VALID_RESPONSE)
    try:
        assert coordinator.data_age_seconds == 120.0
        freezer.tick(60)
        assert coordinator.data_age_seconds == 180.0
        for value in (None, "bad", "2026-08-08T00:00:00"):
            coordinator.data["date"] = value
            assert coordinator.data_age_seconds is None
    finally:
        await coordinator.async_shutdown()


async def test_height_sensor_never_exposes_nan(hass, freezer):
    freezer.move_to("2026-08-08T12:00:00Z")
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    coordinator.data = deepcopy(VALID_RESPONSE)
    coordinator.data["todayTides"][0]["@altura"] = "nan"
    try:
        assert _create_entities("1", coordinator)[3].native_value is None
    finally:
        await coordinator.async_shutdown()

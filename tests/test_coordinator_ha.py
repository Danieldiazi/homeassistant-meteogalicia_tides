"""Home Assistant coordinator error-handling tests."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.meteogalicia_tides.coordinator import (
    MeteoGaliciaTidesCoordinator,
)

VALID_RESPONSE = {
    "pointGeoRSS": "43.36 -8.40",
    "date": "2026-08-08T00:00:00Z",
    "portId": "1",
    "portName": "A Coruña",
    "todayTides": [
        {
            "@id": "0",
            "@hora": "23:59",
            "@idTipoMarea": "1",
            "@estado": "Preamar",
            "@altura": "3,2",
        }
    ],
    "tomorrowFirstTide": {
        "@id": "0",
        "@hora": "01:00",
        "@idTipoMarea": "0",
        "@estado": "Baixamar",
        "@altura": "0,8",
    },
}


async def test_coordinator_accepts_valid_response(hass):
    """A valid API response reaches coordinator entities unchanged."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    with patch.object(
        hass, "async_add_executor_job", AsyncMock(return_value=VALID_RESPONSE)
    ):
        assert await coordinator._async_update_data() == VALID_RESPONSE


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (None, "returned no data"),
        ({}, "invalid response"),
        ({"pointGeoRSS": "43 -8", "todayTides": {}}, "invalid response"),
    ],
)
async def test_coordinator_rejects_empty_or_invalid_response(
    hass, response, message
):
    """Empty and malformed API responses have actionable errors."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    with patch.object(
        hass, "async_add_executor_job", AsyncMock(return_value=response)
    ):
        with pytest.raises(UpdateFailed, match=message):
            await coordinator._async_update_data()


@pytest.mark.parametrize(
    "response",
    [
        {
            "pointGeoRSS": "43 -8",
            "todayTides": [],
            "tomorrowFirstTide": None,
        },
        {
            "pointGeoRSS": "43 -8",
            "todayTides": [{"@hora": "25:99", "@idTipoMarea": "1"}],
            "tomorrowFirstTide": None,
        },
        {
            "pointGeoRSS": "43 -8",
            "todayTides": [{"@hora": "12:00"}],
            "tomorrowFirstTide": None,
        },
    ],
)
async def test_coordinator_rejects_responses_without_usable_tides(
    hass, response
):
    """A structurally valid response still needs a usable tide."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    with patch.object(
        hass, "async_add_executor_job", AsyncMock(return_value=response)
    ):
        with pytest.raises(UpdateFailed, match="invalid response"):
            await coordinator._async_update_data()


async def test_coordinator_reports_timeout(hass):
    """Timeouts are distinguishable from invalid API data."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    with patch.object(
        hass, "async_add_executor_job", AsyncMock(side_effect=TimeoutError)
    ):
        with pytest.raises(UpdateFailed, match="timed out"):
            await coordinator._async_update_data()


async def test_coordinator_reports_unexpected_error(hass):
    """Unexpected client failures preserve useful diagnostic context."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    with patch.object(
        hass,
        "async_add_executor_job",
        AsyncMock(side_effect=RuntimeError("client failure")),
    ):
        with pytest.raises(UpdateFailed, match="client failure"):
            await coordinator._async_update_data()

    assert coordinator.consecutive_failures == 1
    assert coordinator.last_failure_reason.endswith("client failure")
    assert coordinator.update_interval.total_seconds() == 60


async def test_coordinator_restores_interval_after_success(hass):
    """A successful request clears backoff and failure diagnostics."""
    coordinator = MeteoGaliciaTidesCoordinator(hass, "1")
    with patch.object(
        hass,
        "async_add_executor_job",
        AsyncMock(side_effect=[OSError("offline"), VALID_RESPONSE]),
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert await coordinator._async_update_data() == VALID_RESPONSE

    assert coordinator.consecutive_failures == 0
    assert coordinator.last_failure_reason is None
    assert coordinator.last_success is not None
    assert coordinator.last_attempt is not None
    assert coordinator.last_request_duration >= 0
    assert coordinator.update_interval.total_seconds() == 30

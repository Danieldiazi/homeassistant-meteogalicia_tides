"""Regression tests for dated, local tide predictions."""

from datetime import UTC, date, datetime

import pytest

from custom_components.meteogalicia_tides.tide import (
    TIDE_TIME_ZONE,
    tides_on_day,
    upcoming_tides,
    with_forecast_dates,
)


def test_legacy_rss_date_is_fixed_in_galicia():
    """The old library's yesterday timestamp never slides with the clock."""
    original = {"date": "2026-08-06T22:00:00Z"}
    dated = with_forecast_dates(original)
    assert dated["todayDate"] == "2026-08-08"
    assert dated["tomorrowDate"] == "2026-08-09"
    assert dated["date"] == "2026-08-08T00:00:00+02:00"
    assert original == {"date": "2026-08-06T22:00:00Z"}
    assert with_forecast_dates(dated) == dated


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"date": None},
        {"date": "invalid"},
        {"todayDate": "2026-08-08", "tomorrowDate": "2026-08-10"},
    ],
)
def test_invalid_dates_are_rejected(data):
    with pytest.raises((TypeError, ValueError)):
        with_forecast_dates(data)


def test_cached_tides_expire_and_partial_daily_count_is_unknown():
    data = with_forecast_dates(
        {
            "todayDate": "2026-08-08",
            "todayTides": [{"@hora": "23:59"}],
            "tomorrowFirstTide": {"@hora": "01:00"},
        }
    )
    assert upcoming_tides(data, datetime(2026, 8, 10, tzinfo=UTC)) == []
    assert tides_on_day(data, date(2026, 8, 9)) is None
    data["tomorrowTides"] = [{"@hora": "01:00"}, {"@hora": "13:00"}]
    assert len(tides_on_day(data, date(2026, 8, 9))) == 2


def test_times_follow_galicia_calendar_across_daylight_saving_change():
    data = with_forecast_dates(
        {
            "todayDate": "2026-10-24",
            "todayTides": [{"@hora": "23:00"}],
            "tomorrowTides": [{"@hora": "03:30"}],
        }
    )
    candidates = upcoming_tides(data, datetime(2026, 10, 24, 20, tzinfo=UTC))
    assert [when.astimezone(UTC) for _, when in candidates] == [
        datetime(2026, 10, 24, 21, tzinfo=UTC),
        datetime(2026, 10, 25, 2, 30, tzinfo=UTC),
    ]
    assert all(when.tzinfo == TIDE_TIME_ZONE for _, when in candidates)

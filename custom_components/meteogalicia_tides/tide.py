"""Pure helpers for selecting and formatting tide data."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from . import const

TIDE_TIME_ZONE = ZoneInfo("Europe/Madrid")


def with_forecast_dates(data):
    """Attach fixed calendar dates, including the library's 0.1.7 contract."""
    result = dict(data)
    if "todayDate" in result:
        day = date.fromisoformat(result["todayDate"])
    else:
        # 0.1.7 labels date with yesterday's RSS item. Keep its actual day;
        # never reinterpret cached data relative to the time of the next read.
        raw_date = result.get("date")
        if not isinstance(raw_date, str):
            raise ValueError("Missing forecast date")
        timestamp = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=TIDE_TIME_ZONE)
        day = timestamp.astimezone(TIDE_TIME_ZONE).date() + timedelta(days=1)
        result["todayDate"] = day.isoformat()
        result["date"] = datetime.combine(
            day, datetime.min.time(), tzinfo=TIDE_TIME_ZONE
        ).isoformat()
    result.setdefault("tomorrowDate", (day + timedelta(days=1)).isoformat())
    if date.fromisoformat(result["tomorrowDate"]) != day + timedelta(days=1):
        raise ValueError("Inconsistent forecast dates")
    return result


def tides_on_day(data, day):
    """Return complete forecast lists for a specific calendar day."""
    if data.get("todayDate") == day.isoformat():
        return data.get("todayTides")
    if data.get("tomorrowDate") == day.isoformat():
        return data.get("tomorrowTides")
    return None


def upcoming_tides(data, now):
    """Pair future tides with their original timezone-aware timestamps."""
    candidates = []
    tomorrow = data.get("tomorrowTides")
    if tomorrow is None:
        first = data.get("tomorrowFirstTide")
        tomorrow = [first] if first else []
    for field, tides in (
        ("todayDate", data.get("todayTides") or []),
        ("tomorrowDate", tomorrow),
    ):
        try:
            day = date.fromisoformat(data[field])
        except KeyError, TypeError, ValueError:
            continue
        for tide in tides:
            try:
                hour, minute = map(int, tide[const.HORA_FIELD].split(":"))
                timestamp = datetime.combine(
                    day, datetime.min.time(), tzinfo=TIDE_TIME_ZONE
                ).replace(hour=hour, minute=minute)
            except KeyError, TypeError, ValueError:
                continue
            if timestamp.astimezone(UTC) > now.astimezone(UTC):
                candidates.append((tide, timestamp))
    return sorted(candidates, key=lambda item: item[1].astimezone(UTC))


def get_next_tide_with_day(
    today_tides: list[dict[str, Any]] | None,
    tomorrow_first_tide: dict[str, Any] | None,
    now: datetime | None = None,
) -> tuple[dict[str, Any] | None, bool]:
    """Return the next tide and whether it belongs to tomorrow."""
    current = now or datetime.now().astimezone()

    for tide in today_tides or []:
        tide_time = tide.get(const.HORA_FIELD)
        if not isinstance(tide_time, str):
            continue
        try:
            hour, minute = (int(value) for value in tide_time.split(":", 1))
        except TypeError, ValueError:
            continue
        if (hour, minute) > (current.hour, current.minute):
            return tide, False

    return tomorrow_first_tide, tomorrow_first_tide is not None


def get_next_tide(
    today_tides: list[dict[str, Any]] | None,
    tomorrow_first_tide: dict[str, Any] | None,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Return the next tide without relying on external item IDs."""
    return get_next_tide_with_day(today_tides, tomorrow_first_tide, now)[0]


def get_state_from_tide(tide: dict[str, Any] | None) -> str | None:
    """Return the legacy state text for a tide.

    The English text is intentionally preserved because existing automations may
    rely on the sensor state.
    """
    if not tide:
        return None

    tide_type = tide.get(const.ID_TIPO_MAREA_FIELD)
    tide_time = tide.get(const.HORA_FIELD)
    if tide_type is None or not tide_time:
        return None

    try:
        tide_type_int = int(tide_type)
    except TypeError, ValueError:
        return None

    if tide_type_int == 0:
        return f"Low tide at {tide_time}"
    return f"High tide at {tide_time}"

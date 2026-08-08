"""Pure helpers for selecting and formatting tide data."""

from datetime import datetime
from typing import Any

from . import const


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
        except (TypeError, ValueError):
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
    except (TypeError, ValueError):
        return None

    if tide_type_int == 0:
        return f"Low tide at {tide_time}"
    return f"High tide at {tide_time}"

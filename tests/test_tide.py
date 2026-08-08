"""Tests for tide selection helpers."""

from datetime import datetime
import importlib.util
from pathlib import Path
import sys
from types import ModuleType


PACKAGE_NAME = "custom_components.meteogalicia_tides"
PACKAGE_PATH = Path(__file__).parents[1] / "custom_components/meteogalicia_tides"
package = ModuleType(PACKAGE_NAME)
package.__path__ = [str(PACKAGE_PATH)]
sys.modules[PACKAGE_NAME] = package

for module_name in ("const", "tide"):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE_NAME}.{module_name}", PACKAGE_PATH / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

tide_module = sys.modules[f"{PACKAGE_NAME}.tide"]
get_next_tide = tide_module.get_next_tide
get_next_tide_with_day = tide_module.get_next_tide_with_day
get_state_from_tide = tide_module.get_state_from_tide


TODAY = [
    {"@id": "10", "@hora": "01:00", "@idTipoMarea": "1"},
    {"@id": "30", "@hora": "07:15", "@idTipoMarea": "0"},
    {"@id": "50", "@hora": "13:30", "@idTipoMarea": "1"},
]
TOMORROW = {"@id": "0", "@hora": "02:00", "@idTipoMarea": "0"}


def test_selects_first_future_tide_without_using_external_ids():
    """The external @id does not need to match the list position."""
    assert get_next_tide(TODAY, TOMORROW, datetime(2026, 8, 8, 7, 0)) == TODAY[1]


def test_exact_tide_minute_selects_the_following_tide():
    """Preserve the legacy boundary behaviour at the exact tide minute."""
    assert get_next_tide(TODAY, TOMORROW, datetime(2026, 8, 8, 7, 15)) == TODAY[2]


def test_after_last_tide_selects_tomorrow():
    """After today's final tide, select tomorrow's first tide."""
    tide, is_tomorrow = get_next_tide_with_day(
        TODAY, TOMORROW, datetime(2026, 8, 8, 23, 0)
    )
    assert tide == TOMORROW
    assert is_tomorrow is True


def test_skips_malformed_hours():
    """Malformed entries do not prevent selecting a valid tide."""
    tides = [{"@hora": "invalid"}, TODAY[2]]
    assert get_next_tide(tides, TOMORROW, datetime(2026, 8, 8, 10, 0)) == TODAY[2]


def test_legacy_state_text_is_unchanged():
    """Existing automation-facing state values remain unchanged."""
    assert get_state_from_tide(TODAY[0]) == "High tide at 01:00"
    assert get_state_from_tide(TODAY[1]) == "Low tide at 07:15"

"""Compatibility regression checks."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_public_identifiers_are_preserved():
    """Do not silently break installed entities or YAML configuration."""
    const = (ROOT / "custom_components/meteogalicia_tides/const.py").read_text()
    sensor = (ROOT / "custom_components/meteogalicia_tides/sensor.py").read_text()

    assert 'DOMAIN = "meteogalicia_tides"' in const
    assert 'CONF_ID_PORT = "id_port"' in const
    assert "_forecast_tides_id_{self.id}" in sensor
    assert 'return f"{self._name} - Forecast Tides"' in sensor

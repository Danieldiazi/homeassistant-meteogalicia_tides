"""Compatibility regression checks."""

from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class CompatibilityTest(unittest.TestCase):
    """Regression tests for identifiers used by existing installations."""

    def test_public_identifiers_are_preserved(self):
        """Do not break installed entities or YAML configuration."""
        const = (ROOT / "custom_components/meteogalicia_tides/const.py").read_text()
        sensor = (
            ROOT / "custom_components/meteogalicia_tides/sensor.py"
        ).read_text()

        self.assertIn('DOMAIN = "meteogalicia_tides"', const)
        self.assertIn('CONF_ID_PORT = "id_port"', const)
        self.assertIn("_forecast_tides_id_{self.id}", sensor)
        self.assertIn('return f"{self._name} - Forecast Tides"', sensor)

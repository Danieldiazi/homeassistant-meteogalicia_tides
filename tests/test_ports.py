"""Tests for the official MeteoGalicia port catalogue."""

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components/meteogalicia_tides/ports.py"
)
SPEC = importlib.util.spec_from_file_location("meteogalicia_tides_ports", MODULE_PATH)
ports_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ports_module)


class PortsTest(unittest.TestCase):
    """Validate the public port ID-to-name mapping."""

    def test_official_port_mapping(self):
        """Keep the IDs published by MeteoGalicia."""
        self.assertEqual(ports_module.PORTS["1"], "A Coruña")
        self.assertEqual(ports_module.PORTS["3"], "Vigo")
        self.assertEqual(ports_module.PORTS["14"], "Ferrol Porto exterior")
        self.assertEqual(ports_module.PORTS["16"], "Ferrol")
        self.assertEqual(len(ports_module.PORTS), 15)

    def test_unknown_port_has_stable_fallback(self):
        """Legacy YAML IDs remain importable if the catalogue changes."""
        self.assertEqual(ports_module.port_name("99"), "Port 99")

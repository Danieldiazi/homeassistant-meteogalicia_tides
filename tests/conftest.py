"""Shared Home Assistant test configuration."""

pytest_plugins = "pytest_homeassistant_custom_component"


import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load the integration from custom_components in every HA test."""
    yield

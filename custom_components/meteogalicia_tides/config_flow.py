"""Config flow for MeteoGalicia Tides."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import ConfigFlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import CONF_ID_PORT, DOMAIN
from .ports import PORTS, port_name


PORT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID_PORT): SelectSelector(
            SelectSelectorConfig(
                options=[
                    {"label": name, "value": id_port}
                    for id_port, name in PORTS.items()
                ]
            )
        )
    }
)


class MeteoGaliciaTidesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MeteoGalicia Tides."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            id_port = str(user_input[CONF_ID_PORT]).strip()
            if id_port not in PORTS:
                errors[CONF_ID_PORT] = "invalid_port"
            else:
                return await self._async_create_port_entry(id_port)

        return self.async_show_form(
            step_id="user",
            data_schema=PORT_SCHEMA,
            errors=errors,
        )

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Import a port from legacy YAML configuration."""
        id_port = str(import_data[CONF_ID_PORT]).strip()
        if id_port.isdecimal():
            id_port = str(int(id_port))
        return await self._async_create_port_entry(id_port)

    async def _async_create_port_entry(self, id_port: str) -> ConfigFlowResult:
        """Create a port entry while preventing duplicates."""
        await self.async_set_unique_id(id_port)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=port_name(id_port),
            data={CONF_ID_PORT: id_port},
        )

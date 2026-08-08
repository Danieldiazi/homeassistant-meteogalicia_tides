"""Config flow for MeteoGalicia Tides."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import ConfigFlowResult

from .const import CONF_ID_PORT, DOMAIN


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
            if not id_port.isdecimal() or int(id_port) <= 0:
                errors[CONF_ID_PORT] = "invalid_port"
            else:
                id_port = str(int(id_port))
                await self.async_set_unique_id(id_port)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"MeteoGalicia Tides {id_port}",
                    data={CONF_ID_PORT: id_port},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ID_PORT): str}),
            errors=errors,
        )

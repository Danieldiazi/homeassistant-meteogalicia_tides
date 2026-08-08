"""Config flow for MeteoGalicia Tides."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    CONF_ID_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
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

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return MeteoGaliciaTidesOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
        """Import a port from legacy YAML configuration."""
        id_port = str(import_data[CONF_ID_PORT]).strip()
        if id_port.isdecimal():
            id_port = str(int(id_port))
        entry_data = {CONF_ID_PORT: id_port}
        if CONF_SCAN_INTERVAL in import_data:
            entry_data[CONF_SCAN_INTERVAL] = int(import_data[CONF_SCAN_INTERVAL])
        return await self._async_create_port_entry(
            id_port, entry_data, update_existing=True
        )

    async def _async_create_port_entry(
        self,
        id_port: str,
        entry_data: dict[str, Any] | None = None,
        update_existing: bool = False,
    ) -> dict[str, Any]:
        """Create a port entry while preventing duplicates."""
        await self.async_set_unique_id(id_port)
        self._abort_if_unique_id_configured(
            updates=entry_data if update_existing else None
        )
        return self.async_create_entry(
            title=port_name(id_port),
            data=entry_data or {CONF_ID_PORT: id_port},
        )


class MeteoGaliciaTidesOptionsFlow(config_entries.OptionsFlow):
    """Handle MeteoGalicia Tides options."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Configure the polling interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            ),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                        ),
                    )
                }
            ),
        )

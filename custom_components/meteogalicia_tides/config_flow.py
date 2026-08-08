"""Config flow for MeteoGalicia Tides."""

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ID_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    TIMEOUT,
)
from .coordinator import _get_forecast_tide_data_from_api, _is_valid_response
from .ports import PORTS, port_name

SCAN_INTERVAL_OPTIONS = [
    {"label": "30 seconds", "value": "30"},
    {"label": "1 minute", "value": "60"},
    {"label": "5 minutes", "value": "300"},
    {"label": "15 minutes", "value": "900"},
    {"label": "30 minutes", "value": "1800"},
    {"label": "1 hour", "value": "3600"},
    {"label": "6 hours", "value": "21600"},
    {"label": "24 hours", "value": "86400"},
]

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
        return MeteoGaliciaTidesOptionsFlow()

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
                await self.async_set_unique_id(id_port)
                self._abort_if_unique_id_configured()
                try:
                    async with asyncio.timeout(TIMEOUT):
                        response = await self.hass.async_add_executor_job(
                            _get_forecast_tide_data_from_api, id_port
                        )
                except (TimeoutError, OSError):
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    errors["base"] = "unknown"
                else:
                    if not _is_valid_response(response):
                        errors["base"] = "invalid_response"
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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Configure the polling interval."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                interval = int(user_input[CONF_SCAN_INTERVAL])
            except (TypeError, ValueError):
                errors["base"] = "invalid_interval"
            else:
                if MIN_SCAN_INTERVAL <= interval <= MAX_SCAN_INTERVAL:
                    return self.async_create_entry(
                        title="", data={CONF_SCAN_INTERVAL: interval}
                    )
                errors["base"] = "invalid_interval"

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
                        CONF_SCAN_INTERVAL, default=str(current_interval)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=SCAN_INTERVAL_OPTIONS,
                            custom_value=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

"""Config flow for Gas & Water Meter integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_CALORIFIC_VALUE,
    CONF_CONDITION_FACTOR,
    CONF_CURRENCY,
    CONF_METER_NAME,
    CONF_METER_NUMBER,
    CONF_METER_TYPE,
    CURRENCIES,
    DEFAULT_CALORIFIC_VALUE,
    DEFAULT_CONDITION_FACTOR,
    DEFAULT_CURRENCY,
    DOMAIN,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
)


class GasWaterMeterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gas & Water Meter."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step -- meter setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            meter_type = user_input[CONF_METER_TYPE]
            meter_number = user_input[CONF_METER_NUMBER]

            # Set unique ID based on meter type and number
            unique_id = f"{DOMAIN}_{meter_type}_{meter_number}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Validate meter number is not empty
            if not meter_number.strip():
                errors[CONF_METER_NUMBER] = "empty_meter_number"
            # Validate meter name is not empty
            elif not user_input[CONF_METER_NAME].strip():
                errors[CONF_METER_NAME] = "empty_meter_name"
            else:
                # For gas meters, proceed to gas_params step
                if meter_type == METER_TYPE_GAS:
                    self._user_data = user_input
                    return await self.async_step_gas_params()

                # For water meters, create entry directly
                title = f"{user_input[CONF_METER_NAME]} ({meter_type.capitalize()})"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_METER_TYPE, default=METER_TYPE_GAS): vol.In(
                        {
                            METER_TYPE_GAS: "Gas",
                            METER_TYPE_WATER: "Water",
                        }
                    ),
                    vol.Required(CONF_METER_NAME): str,
                    vol.Required(CONF_METER_NUMBER): str,
                    vol.Required(CONF_CURRENCY, default=DEFAULT_CURRENCY): vol.In(CURRENCIES),
                }
            ),
            errors=errors,
        )

    async def async_step_gas_params(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the gas-specific parameters step (calorific value, condition factor)."""
        if user_input is not None:
            data = {**self._user_data, **user_input}
            title = f"{data[CONF_METER_NAME]} ({data[CONF_METER_TYPE].capitalize()})"
            return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="gas_params",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CALORIFIC_VALUE,
                        default=DEFAULT_CALORIFIC_VALUE,
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_CONDITION_FACTOR,
                        default=DEFAULT_CONDITION_FACTOR,
                    ): vol.Coerce(float),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> GasWaterMeterOptionsFlow:
        """Get the options flow handler."""
        return GasWaterMeterOptionsFlow(config_entry)


class GasWaterMeterOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Gas & Water Meter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry data with new values
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data=user_input)

        current_data = self.config_entry.data
        is_gas = current_data.get(CONF_METER_TYPE) == METER_TYPE_GAS

        schema_fields: dict[vol.Marker, Any] = {
            vol.Required(
                CONF_METER_NUMBER,
                default=current_data.get(CONF_METER_NUMBER, ""),
            ): str,
            vol.Required(
                CONF_CURRENCY,
                default=current_data.get(CONF_CURRENCY, DEFAULT_CURRENCY),
            ): vol.In(CURRENCIES),
        }

        # Add gas-specific fields
        if is_gas:
            schema_fields[
                vol.Required(
                    CONF_CALORIFIC_VALUE,
                    default=current_data.get(CONF_CALORIFIC_VALUE, DEFAULT_CALORIFIC_VALUE),
                )
            ] = vol.Coerce(float)
            schema_fields[
                vol.Required(
                    CONF_CONDITION_FACTOR,
                    default=current_data.get(CONF_CONDITION_FACTOR, DEFAULT_CONDITION_FACTOR),
                )
            ] = vol.Coerce(float)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields),
        )

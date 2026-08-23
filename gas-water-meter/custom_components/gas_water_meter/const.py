"""Constants for the Gas & Water Meter integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "gas_water_meter"
PLATFORMS = [Platform.SENSOR]

# Common icon constants
ICON_GAS_BURNER = "mdi:gas-burner"
ICON_CURRENCY_EUR = "mdi:currency-eur"
ICON_WATER = "mdi:water"

# Config keys
CONF_METER_TYPE = "meter_type"
CONF_METER_NAME = "meter_name"
CONF_METER_NUMBER = "meter_number"
CONF_CURRENCY = "currency"

# Gas-specific config keys
CONF_CALORIFIC_VALUE = "calorific_value"
CONF_CONDITION_FACTOR = "condition_factor"

# Meter types
METER_TYPE_GAS = "gas"
METER_TYPE_WATER = "water"
METER_TYPES = [METER_TYPE_GAS, METER_TYPE_WATER]

# Default values
DEFAULT_CURRENCY = "EUR"
CURRENCIES = ["EUR", "USD", "GBP", "CHF"]

# Gas conversion defaults (typical German utility values)
DEFAULT_CALORIFIC_VALUE = 11.465  # kWh/m³ (Brennwert)
DEFAULT_CONDITION_FACTOR = 0.9684  # Zustandszahl

# Storage
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "gas_water_meter"

# Projection constants
DAYS_PER_MONTH = 30.44
DAYS_PER_YEAR = 365.25

# Icon mappings per meter type
ICONS = {
    METER_TYPE_GAS: {
        "device": "mdi:meter-gas",
        "reading": "mdi:meter-gas",
        "meter_number": "mdi:identifier",
        "last_entry_date": "mdi:calendar-clock",
        "consumption": "mdi:gas-burner",
        "energy_consumption": "mdi:lightning-bolt",
        "days_between": "mdi:calendar-range",
        "daily_average": "mdi:gas-burner",
        "monthly_projection": ICON_GAS_BURNER,
        "yearly_projection": ICON_GAS_BURNER,
        "current_price": ICON_CURRENCY_EUR,
        "last_period_cost": ICON_CURRENCY_EUR,
        "monthly_projected_cost": ICON_CURRENCY_EUR,
        "yearly_projected_cost": ICON_CURRENCY_EUR,
    },
    METER_TYPE_WATER: {
        "device": "mdi:water",
        "reading": "mdi:water-pump",
        "meter_number": "mdi:identifier",
        "last_entry_date": "mdi:calendar-clock",
        "consumption": ICON_WATER,
        "days_between": "mdi:calendar-range",
        "daily_average": ICON_WATER,
        "monthly_projection": ICON_WATER,
        "yearly_projection": ICON_WATER,
        "current_price": ICON_CURRENCY_EUR,
        "last_period_cost": ICON_CURRENCY_EUR,
        "monthly_projected_cost": ICON_CURRENCY_EUR,
        "yearly_projected_cost": ICON_CURRENCY_EUR,
    },
}

# Device name prefixes per meter type (used for device naming)
DEVICE_NAME_PREFIX = {
    METER_TYPE_GAS: "Gas Meter",
    METER_TYPE_WATER: "Water Meter",
}

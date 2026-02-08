"""Constants for the Gas & Water Meter integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "gas_water_meter"
PLATFORMS = [Platform.SENSOR]

# Config keys
CONF_METER_TYPE = "meter_type"
CONF_METER_NAME = "meter_name"
CONF_METER_NUMBER = "meter_number"
CONF_CURRENCY = "currency"

# Meter types
METER_TYPE_GAS = "gas"
METER_TYPE_WATER = "water"
METER_TYPES = [METER_TYPE_GAS, METER_TYPE_WATER]

# Default values
DEFAULT_CURRENCY = "EUR"
CURRENCIES = ["EUR", "USD", "GBP", "CHF"]

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
        "days_between": "mdi:calendar-range",
        "daily_average": "mdi:gas-burner",
        "monthly_projection": "mdi:gas-burner",
        "yearly_projection": "mdi:gas-burner",
        "current_price": "mdi:currency-eur",
        "last_period_cost": "mdi:currency-eur",
        "monthly_projected_cost": "mdi:currency-eur",
        "yearly_projected_cost": "mdi:currency-eur",
    },
    METER_TYPE_WATER: {
        "device": "mdi:water",
        "reading": "mdi:water-pump",
        "meter_number": "mdi:identifier",
        "last_entry_date": "mdi:calendar-clock",
        "consumption": "mdi:water",
        "days_between": "mdi:calendar-range",
        "daily_average": "mdi:water",
        "monthly_projection": "mdi:water",
        "yearly_projection": "mdi:water",
        "current_price": "mdi:currency-eur",
        "last_period_cost": "mdi:currency-eur",
        "monthly_projected_cost": "mdi:currency-eur",
        "yearly_projected_cost": "mdi:currency-eur",
    },
}

# Device name prefixes per meter type (used for device naming)
DEVICE_NAME_PREFIX = {
    METER_TYPE_GAS: "Gas Meter",
    METER_TYPE_WATER: "Water Meter",
}

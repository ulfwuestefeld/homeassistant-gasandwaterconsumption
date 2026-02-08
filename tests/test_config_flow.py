"""Tests for the Gas & Water Meter config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.gas_water_meter.const import (
    CONF_CURRENCY,
    CONF_METER_NAME,
    CONF_METER_NUMBER,
    CONF_METER_TYPE,
    DOMAIN,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
)

from .conftest import MOCK_GAS_CONFIG


async def test_user_flow_gas_success(hass: HomeAssistant) -> None:
    """Test successful gas meter config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_GAS_CONFIG,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kitchen (Gas)"
    assert result["data"][CONF_METER_TYPE] == METER_TYPE_GAS
    assert result["data"][CONF_METER_NAME] == "Kitchen"
    assert result["data"][CONF_METER_NUMBER] == "GAS-12345"
    assert result["data"][CONF_CURRENCY] == "EUR"


async def test_user_flow_water_success(hass: HomeAssistant) -> None:
    """Test successful water meter config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_METER_TYPE: METER_TYPE_WATER,
            CONF_METER_NAME: "Garden",
            CONF_METER_NUMBER: "WAT-67890",
            CONF_CURRENCY: "CHF",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Garden (Water)"
    assert result["data"][CONF_METER_TYPE] == METER_TYPE_WATER
    assert result["data"][CONF_CURRENCY] == "CHF"


async def test_user_flow_empty_meter_number(hass: HomeAssistant) -> None:
    """Test config flow rejects empty meter number."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_METER_TYPE: METER_TYPE_GAS,
            CONF_METER_NAME: "Kitchen",
            CONF_METER_NUMBER: "   ",
            CONF_CURRENCY: "EUR",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_METER_NUMBER: "empty_meter_number"}


async def test_user_flow_empty_meter_name(hass: HomeAssistant) -> None:
    """Test config flow rejects empty meter name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_METER_TYPE: METER_TYPE_GAS,
            CONF_METER_NAME: "   ",
            CONF_METER_NUMBER: "GAS-12345",
            CONF_CURRENCY: "EUR",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_METER_NAME: "empty_meter_name"}


async def test_user_flow_already_configured(hass: HomeAssistant) -> None:
    """Test config flow aborts when meter is already configured."""
    # Create an existing entry first
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_GAS_CONFIG,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Try to create the same meter again
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_GAS_CONFIG,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_multiple_meters_allowed(hass: HomeAssistant) -> None:
    """Test that multiple different meters can be configured."""
    # Add gas meter
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_GAS_CONFIG,
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Add water meter (different type + number = different unique ID)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_METER_TYPE: METER_TYPE_WATER,
            CONF_METER_NAME: "Garden",
            CONF_METER_NUMBER: "WAT-67890",
            CONF_CURRENCY: "EUR",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Verify both entries exist
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2

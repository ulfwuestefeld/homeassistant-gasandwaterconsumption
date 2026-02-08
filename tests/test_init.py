"""Tests for the Gas & Water Meter integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.gas_water_meter.const import DOMAIN

from .conftest import MOCK_GAS_CONFIG, MOCK_STORE_DATA

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from unittest.mock import MagicMock as MockConfigEntry


async def test_setup_entry(hass: HomeAssistant, mock_store_load, mock_store_save) -> None:
    """Test successful integration setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert entry.state is config_entries.ConfigEntryState.LOADED

    # Verify services are registered
    assert hass.services.has_service(DOMAIN, "record_reading")
    assert hass.services.has_service(DOMAIN, "set_price")
    assert hass.services.has_service(DOMAIN, "read_meter_image")


async def test_unload_entry(hass: HomeAssistant, mock_store_load, mock_store_save) -> None:
    """Test successful integration unload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.LOADED

    result = await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert entry.state is config_entries.ConfigEntryState.NOT_LOADED


async def test_setup_entry_empty_store(
    hass: HomeAssistant, mock_store_empty, mock_store_save
) -> None:
    """Test setup with empty store (first run)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert entry.state is config_entries.ConfigEntryState.LOADED

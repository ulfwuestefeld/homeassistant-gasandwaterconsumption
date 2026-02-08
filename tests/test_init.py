"""Tests for the Gas & Water Meter integration setup and unload."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from custom_components.gas_water_meter.const import DOMAIN
from custom_components.gas_water_meter.db import MeterDatabase
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .conftest import MOCK_GAS_CONFIG, MOCK_WATER_CONFIG

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from unittest.mock import MagicMock as MockConfigEntry


async def _setup_domain_with_db(hass: HomeAssistant) -> MeterDatabase:
    """Pre-initialize the domain data with a real temp DB."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    with patch.object(hass.config, "path", return_value=tmp_path):
        db = MeterDatabase(hass)
        await db.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["db"] = db
    hass.data[DOMAIN]["ws_registered"] = True
    hass.data[DOMAIN]["http_registered"] = True
    hass.data[DOMAIN]["panel_registered"] = True

    # Ensure DB is closed when HA stops
    async def _close(event):
        await db.async_close()

    hass.bus.async_listen_once("homeassistant_stop", _close)

    return db


async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test successful integration setup."""
    await _setup_domain_with_db(hass)

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


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test successful integration unload."""
    await _setup_domain_with_db(hass)

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


async def test_setup_entry_empty_db(hass: HomeAssistant) -> None:
    """Test setup with empty database (first run)."""
    await _setup_domain_with_db(hass)

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


async def test_unload_removes_services_on_last_entry(hass: HomeAssistant) -> None:
    """Test that services are removed when the last config entry is unloaded."""
    await _setup_domain_with_db(hass)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "record_reading")

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Services should be removed since this was the last entry
    assert not hass.services.has_service(DOMAIN, "record_reading")
    assert not hass.services.has_service(DOMAIN, "set_price")
    assert not hass.services.has_service(DOMAIN, "read_meter_image")


async def test_unload_keeps_services_with_remaining_entries(hass: HomeAssistant) -> None:
    """Test that services remain when other config entries are still loaded."""
    await _setup_domain_with_db(hass)

    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry1.add_to_hass(hass)

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_WAT-67890",
    )
    entry2.add_to_hass(hass)

    await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    # HA may auto-setup entry2 when it sees a second entry in the same domain.
    # If not already loaded, set it up explicitly.
    if entry2.state is not config_entries.ConfigEntryState.LOADED:
        await hass.config_entries.async_setup(entry2.entry_id)
        await hass.async_block_till_done()

    assert entry1.state is config_entries.ConfigEntryState.LOADED
    assert entry2.state is config_entries.ConfigEntryState.LOADED

    # Unload only the first entry
    await hass.config_entries.async_unload(entry1.entry_id)
    await hass.async_block_till_done()

    # Services should still be registered because entry2 is still loaded
    assert hass.services.has_service(DOMAIN, "record_reading")
    assert hass.services.has_service(DOMAIN, "set_price")
    assert hass.services.has_service(DOMAIN, "read_meter_image")

"""Tests for the Gas & Water Meter sensor platform."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest
from custom_components.gas_water_meter.const import DOMAIN
from custom_components.gas_water_meter.db import MeterDatabase
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant

from .conftest import MOCK_GAS_CONFIG, MOCK_PRICES, MOCK_READINGS, MOCK_WATER_CONFIG

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from unittest.mock import MagicMock as MockConfigEntry


async def _setup_entry(
    hass: HomeAssistant,
    config: dict,
    unique_id: str,
    *,
    populate_data: bool = True,
    entry_id: str = "test_entry",
) -> MockConfigEntry:
    """Set up a config entry with a real temp DB for testing."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    with patch.object(hass.config, "path", return_value=tmp_path):
        db = MeterDatabase(hass)
        await db.async_setup()

    if populate_data:
        for r in MOCK_READINGS:
            await db.async_add_reading(
                entry_id=entry_id,
                meter_number=r["meter_number"],
                reading=r["reading"],
                timestamp=r["timestamp"],
                image_path=r["image_path"],
            )
        for p in MOCK_PRICES:
            await db.async_add_price(
                entry_id=entry_id,
                price_per_unit=p["price_per_unit"],
                valid_from=p["valid_from"],
                valid_to=p["valid_to"],
                currency=p["currency"],
            )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["db"] = db
    hass.data[DOMAIN]["ws_registered"] = True
    hass.data[DOMAIN]["http_registered"] = True
    hass.data[DOMAIN]["panel_registered"] = True

    # Ensure DB is closed when HA stops
    async def _close(event):
        await db.async_close()

    hass.bus.async_listen_once("homeassistant_stop", _close)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=config,
        unique_id=unique_id,
        entry_id=entry_id,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    return entry


async def test_gas_reading_sensor(hass: HomeAssistant) -> None:
    """Test the gas meter reading sensor has correct attributes."""
    await _setup_entry(hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345")

    # Find the reading sensor
    states = hass.states.async_all("sensor")
    reading_states = [s for s in states if s.entity_id.endswith("_meter_reading")]

    assert len(reading_states) >= 1
    state = reading_states[0]

    assert state.state == "125.3"
    assert state.attributes.get("unit_of_measurement") == UnitOfVolume.CUBIC_METERS
    assert state.attributes.get("device_class") == SensorDeviceClass.GAS
    assert state.attributes.get("state_class") == SensorStateClass.TOTAL_INCREASING


async def test_water_reading_sensor(hass: HomeAssistant) -> None:
    """Test the water meter reading sensor has water device class."""
    await _setup_entry(
        hass,
        MOCK_WATER_CONFIG,
        "gas_water_meter_water_WAT-67890",
    )

    states = hass.states.async_all("sensor")
    reading_states = [s for s in states if s.entity_id.endswith("_meter_reading")]

    assert len(reading_states) >= 1
    state = reading_states[0]

    assert state.attributes.get("device_class") == SensorDeviceClass.WATER


async def test_consumption_sensor(hass: HomeAssistant) -> None:
    """Test the consumption sensor shows the delta."""
    await _setup_entry(hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345")

    states = hass.states.async_all("sensor")
    consumption_states = [s for s in states if s.entity_id.endswith("_last_consumption")]

    assert len(consumption_states) >= 1
    state = consumption_states[0]

    # 125.3 - 110.5 = 14.8
    assert float(state.state) == pytest.approx(14.8, abs=0.01)


async def test_projection_sensors(hass: HomeAssistant) -> None:
    """Test projection sensors have values when enough data exists."""
    await _setup_entry(hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345")

    states = hass.states.async_all("sensor")
    daily_avg = [s for s in states if s.entity_id.endswith("_daily_average_consumption")]
    monthly_proj = [s for s in states if s.entity_id.endswith("_monthly_projection")]
    yearly_proj = [s for s in states if s.entity_id.endswith("_yearly_projection")]

    assert len(daily_avg) >= 1
    assert len(monthly_proj) >= 1
    assert len(yearly_proj) >= 1

    # Daily average should be positive
    assert float(daily_avg[0].state) > 0
    # Monthly and yearly should be larger than daily
    assert float(monthly_proj[0].state) > float(daily_avg[0].state)
    assert float(yearly_proj[0].state) > float(monthly_proj[0].state)


async def test_cost_sensors(hass: HomeAssistant) -> None:
    """Test cost sensors have values when prices are configured."""
    await _setup_entry(hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345")

    states = hass.states.async_all("sensor")
    current_price = [s for s in states if s.entity_id.endswith("_current_price")]
    last_cost = [s for s in states if s.entity_id.endswith("_last_period_cost")]

    assert len(current_price) >= 1
    assert len(last_cost) >= 1

    assert float(current_price[0].state) == 1.85
    assert float(last_cost[0].state) > 0


async def test_empty_db_sensors_unknown(hass: HomeAssistant) -> None:
    """Test that sensors show unknown state with empty database."""
    await _setup_entry(
        hass,
        MOCK_GAS_CONFIG,
        "gas_water_meter_gas_GAS-12345",
        populate_data=False,
    )

    states = hass.states.async_all("sensor")
    reading_states = [s for s in states if s.entity_id.endswith("_meter_reading")]

    assert len(reading_states) >= 1
    # With no readings, the state should be unknown
    assert reading_states[0].state == "unknown"


async def test_gas_sensors_created(hass: HomeAssistant) -> None:
    """Test creation of 15 gas meter sensors (12 common + 2 energy + base_fee)."""
    await _setup_entry(hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345")

    states = hass.states.async_all("sensor")
    our_sensors = [s for s in states if s.entity_id.startswith("sensor.gas_meter")]

    assert len(our_sensors) == 15
    # Verify energy_consumption sensors exist (energy_consumption + energy_consumption_total)
    energy_sensors = [s for s in our_sensors if "energy_consumption" in s.entity_id]
    assert len(energy_sensors) == 2


async def test_water_sensors_created(hass: HomeAssistant) -> None:
    """Test that exactly 13 sensors are created for a water meter (no energy_consumption, but current_base_fee)."""
    await _setup_entry(hass, MOCK_WATER_CONFIG, "gas_water_meter_water_WAT-67890")

    states = hass.states.async_all("sensor")
    our_sensors = [s for s in states if s.entity_id.startswith("sensor.water_meter")]

    assert len(our_sensors) == 13
    # Verify energy_consumption sensor does NOT exist
    energy_sensors = [s for s in our_sensors if "energy_consumption" in s.entity_id]
    assert len(energy_sensors) == 0


async def test_sensors_update_after_db_write_and_refresh(hass: HomeAssistant) -> None:
    """Test that sensors update from 'unknown' to actual values after DB write + refresh.

    This is the end-to-end test for the reported issue: sensors must reflect
    data entered via the GUI (WebSocket → DB → coordinator refresh → sensor state).
    """
    entry = await _setup_entry(
        hass,
        MOCK_GAS_CONFIG,
        "gas_water_meter_gas_GAS-12345",
        populate_data=False,
    )

    # --- Verify sensors start as "unknown" ---
    states = hass.states.async_all("sensor")
    reading_sensor = next(s for s in states if s.entity_id.endswith("_meter_reading"))
    consumption_sensor = next(s for s in states if s.entity_id.endswith("_last_consumption"))

    assert reading_sensor.state == "unknown"
    assert consumption_sensor.state == "unknown"

    # --- Write first reading directly to the shared DB ---
    db: MeterDatabase = hass.data[DOMAIN]["db"]
    await db.async_add_reading(
        entry_id=entry.entry_id,
        meter_number="GAS-12345",
        reading=100.0,
        timestamp="2026-01-01T10:00:00+00:00",
    )

    # Refresh coordinator (immediate, bypasses debouncer)
    coordinator = entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # --- Verify reading sensor updated ---
    reading_state = hass.states.get(reading_sensor.entity_id)
    assert reading_state is not None
    assert reading_state.state == "100.0"

    # Consumption still unknown (only 1 reading)
    cons_state = hass.states.get(consumption_sensor.entity_id)
    assert cons_state.state == "unknown"

    # --- Write second reading ---
    await db.async_add_reading(
        entry_id=entry.entry_id,
        meter_number="GAS-12345",
        reading=112.5,
        timestamp="2026-01-15T10:00:00+00:00",
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # --- Verify both sensors updated ---
    reading_state = hass.states.get(reading_sensor.entity_id)
    assert reading_state.state == "112.5"

    cons_state = hass.states.get(consumption_sensor.entity_id)
    assert float(cons_state.state) == pytest.approx(12.5, abs=0.01)

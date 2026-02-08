"""Tests for the Gas & Water Meter sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfVolume
from homeassistant.core import HomeAssistant

from custom_components.gas_water_meter.const import DOMAIN, METER_TYPE_GAS, METER_TYPE_WATER

from .conftest import MOCK_GAS_CONFIG, MOCK_STORE_DATA, MOCK_WATER_CONFIG

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from unittest.mock import MagicMock as MockConfigEntry


async def _setup_entry(
    hass: HomeAssistant,
    config: dict,
    unique_id: str,
    store_data: dict | None = None,
) -> MockConfigEntry:
    """Set up a config entry for testing."""
    with patch(
        "custom_components.gas_water_meter.store.Store.async_load",
        return_value=store_data or MOCK_STORE_DATA,
    ), patch(
        "custom_components.gas_water_meter.store.Store.async_save",
        new_callable=AsyncMock,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data=config,
            unique_id=unique_id,
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_gas_reading_sensor(hass: HomeAssistant) -> None:
    """Test the gas meter reading sensor has correct attributes."""
    entry = await _setup_entry(
        hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345"
    )

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
    water_store_data = {**MOCK_STORE_DATA, "meter_type": "water"}

    entry = await _setup_entry(
        hass,
        MOCK_WATER_CONFIG,
        "gas_water_meter_water_WAT-67890",
        store_data=water_store_data,
    )

    states = hass.states.async_all("sensor")
    reading_states = [s for s in states if s.entity_id.endswith("_meter_reading")]

    assert len(reading_states) >= 1
    state = reading_states[0]

    assert state.attributes.get("device_class") == SensorDeviceClass.WATER


async def test_consumption_sensor(hass: HomeAssistant) -> None:
    """Test the consumption sensor shows the delta."""
    entry = await _setup_entry(
        hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345"
    )

    states = hass.states.async_all("sensor")
    consumption_states = [s for s in states if s.entity_id.endswith("_last_consumption")]

    assert len(consumption_states) >= 1
    state = consumption_states[0]

    # 125.3 - 110.5 = 14.8
    assert float(state.state) == pytest.approx(14.8, abs=0.01)


async def test_projection_sensors(hass: HomeAssistant) -> None:
    """Test projection sensors have values when enough data exists."""
    entry = await _setup_entry(
        hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345"
    )

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
    entry = await _setup_entry(
        hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345"
    )

    states = hass.states.async_all("sensor")
    current_price = [s for s in states if s.entity_id.endswith("_current_price")]
    last_cost = [s for s in states if s.entity_id.endswith("_last_period_cost")]

    assert len(current_price) >= 1
    assert len(last_cost) >= 1

    assert float(current_price[0].state) == 1.85
    assert float(last_cost[0].state) > 0


async def test_empty_store_sensors_unknown(hass: HomeAssistant) -> None:
    """Test that sensors show unknown state with empty store."""
    empty_store = {
        "meter_type": "gas",
        "meter_name": "Kitchen",
        "meter_number": "GAS-12345",
        "currency": "EUR",
        "readings": [],
        "prices": [],
    }

    entry = await _setup_entry(
        hass,
        MOCK_GAS_CONFIG,
        "gas_water_meter_gas_GAS-12345",
        store_data=empty_store,
    )

    states = hass.states.async_all("sensor")
    reading_states = [s for s in states if s.entity_id.endswith("_meter_reading")]

    assert len(reading_states) >= 1
    # With no readings, the state should be unknown
    assert reading_states[0].state == "unknown"


async def test_twelve_sensors_created(hass: HomeAssistant) -> None:
    """Test that exactly 12 sensors are created per meter."""
    entry = await _setup_entry(
        hass, MOCK_GAS_CONFIG, "gas_water_meter_gas_GAS-12345"
    )

    states = hass.states.async_all("sensor")
    # Filter to only sensors from our integration
    our_sensors = [
        s for s in states
        if s.entity_id.startswith("sensor.gas_meter")
    ]

    assert len(our_sensors) == 12

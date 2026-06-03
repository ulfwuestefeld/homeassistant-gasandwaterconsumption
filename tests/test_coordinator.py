"""Tests for the Gas & Water Meter coordinator (projection + cost logic)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from custom_components.gas_water_meter.const import DAYS_PER_MONTH, DAYS_PER_YEAR
from custom_components.gas_water_meter.coordinator import (
    _UPDATE_INTERVAL,
    MeterCoordinator,
    _days_between,
)
from custom_components.gas_water_meter.db import MeterDatabase
from custom_components.gas_water_meter.websocket import (
    _refresh_all_coordinators,
    _refresh_coordinator,
)
from homeassistant.core import HomeAssistant

from .conftest import MOCK_GAS_CONFIG, MOCK_WATER_CONFIG

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from unittest.mock import MagicMock as MockConfigEntry


def test_days_between_calculation() -> None:
    """Test the _days_between helper function."""
    result = _days_between(
        "2026-01-01T10:00:00+00:00",
        "2026-01-15T10:00:00+00:00",
    )
    assert result is not None
    assert abs(result - 14.0) < 0.001

    result = _days_between(
        "2026-01-01T00:00:00+00:00",
        "2026-02-01T00:00:00+00:00",
    )
    assert result is not None
    assert abs(result - 31.0) < 0.001


def test_days_between_invalid_timestamps() -> None:
    """Test _days_between with invalid input."""
    assert _days_between("invalid", "2026-01-01T10:00:00+00:00") is None
    assert _days_between("2026-01-01T10:00:00+00:00", "invalid") is None


async def test_coordinator_computes_core_data(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that coordinator computes core sensor values correctly."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Reading
    assert data.reading == 125.3

    # Meter number from last reading
    assert data.meter_number == "GAS-12345"

    # Consumption (delta between last two: 125.3 - 110.5)
    assert data.consumption is not None
    assert abs(data.consumption - 14.8) < 0.001

    # Days between last two readings (Jan 15 to Feb 1 = 17 days)
    assert data.days_between is not None
    assert abs(data.days_between - 17.0) < 0.1


async def test_coordinator_computes_projection(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test projection calculations."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Total consumption: 125.3 - 100.0 = 25.3
    # Total days: Jan 1 to Feb 1 = 31 days
    # Daily average: 25.3 / 31 ~ 0.8161
    assert data.daily_average is not None
    assert abs(data.daily_average - (25.3 / 31.0)) < 0.001

    # Monthly projection
    expected_monthly = data.daily_average * DAYS_PER_MONTH
    assert data.monthly_projection is not None
    assert abs(data.monthly_projection - expected_monthly) < 0.1

    # Yearly projection
    expected_yearly = data.daily_average * DAYS_PER_YEAR
    assert data.yearly_projection is not None
    assert abs(data.yearly_projection - expected_yearly) < 1.0


async def test_coordinator_computes_costs(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test cost calculations for gas (ct/kWh pricing)."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Current price should be 1.85 (ct/kWh, valid from 2026-01-01)
    assert data.current_price == 1.85

    # Gas conversion factors should be exposed
    assert data.calorific_value == 11.465
    assert data.condition_factor == 0.9684

    # Energy consumption for last period (14.8 m³)
    # kWh = 14.8 * 11.465 * 0.9684 = ~164.224
    assert data.energy_consumption is not None
    expected_kwh = 14.8 * 11.465 * 0.9684
    assert abs(data.energy_consumption - round(expected_kwh, 3)) < 0.01

    # Last period cost for gas: kWh * price(ct/kWh) / 100 = EUR
    # Previous reading is 2026-01-15, price at that date is 1.85 ct/kWh
    assert data.last_period_cost is not None
    expected_cost = round(expected_kwh * 1.85 / 100.0, 2)
    assert abs(data.last_period_cost - expected_cost) < 0.01

    # Monthly projected cost
    assert data.monthly_projected_cost is not None

    # Yearly projected cost
    assert data.yearly_projected_cost is not None


async def test_coordinator_empty_db(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test coordinator with no readings."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db_empty)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # All values should be None
    assert data.reading is None
    assert data.meter_number is None
    assert data.consumption is None
    assert data.days_between is None
    assert data.daily_average is None
    assert data.monthly_projection is None
    assert data.yearly_projection is None
    assert data.current_price is None
    assert data.last_period_cost is None
    assert data.monthly_projected_cost is None
    assert data.yearly_projected_cost is None


async def test_coordinator_single_reading(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test coordinator with only one reading (no delta/projection possible)."""
    db = mock_db_empty

    await db.async_add_reading(
        entry_id="test_entry",
        meter_number="GAS-12345",
        reading=100.0,
        timestamp="2026-01-01T10:00:00+00:00",
    )

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Reading exists
    assert data.reading == 100.0
    assert data.meter_number == "GAS-12345"

    # No delta/projection with single reading
    assert data.consumption is None
    assert data.days_between is None
    assert data.daily_average is None
    assert data.monthly_projection is None
    assert data.yearly_projection is None


def test_coordinator_has_polling_interval() -> None:
    """Test that the safety-net polling interval is 60 seconds."""
    assert timedelta(seconds=60) == _UPDATE_INTERVAL


async def test_coordinator_update_interval_set(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that the coordinator instance uses the 60-second update interval."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db_empty)

    assert coordinator.update_interval == timedelta(seconds=60)


async def test_coordinator_reflects_new_data_after_refresh(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that coordinator picks up new DB data after explicit refresh.

    This simulates the real-world flow: integration starts with empty DB,
    user enters data via GUI (WebSocket), coordinator is refreshed, and
    sensor values must reflect the new data.

    Uses ``async_refresh()`` (immediate, bypasses debouncer) to verify the
    data pipeline without timing dependencies.
    """
    db = mock_db_empty

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    # Initially empty -- no readings
    assert coordinator.data is not None
    assert coordinator.data.reading is None
    assert coordinator.data.consumption is None

    # --- Simulate user entering first reading via GUI ---
    await db.async_add_reading(
        entry_id="test_entry",
        meter_number="GAS-12345",
        reading=100.0,
        timestamp="2026-01-01T10:00:00+00:00",
    )
    await coordinator.async_refresh()

    assert coordinator.data.reading == 100.0
    assert coordinator.data.meter_number == "GAS-12345"
    assert coordinator.data.consumption is None  # only 1 reading, no delta

    # --- Simulate user entering second reading ---
    await db.async_add_reading(
        entry_id="test_entry",
        meter_number="GAS-12345",
        reading=115.7,
        timestamp="2026-01-20T10:00:00+00:00",
    )
    await coordinator.async_refresh()

    assert coordinator.data.reading == 115.7
    assert coordinator.data.consumption is not None
    assert abs(coordinator.data.consumption - 15.7) < 0.001
    assert coordinator.data.daily_average is not None

    # Clean up the coordinator's internal debouncer/timer
    await coordinator.async_shutdown()


async def test_refresh_coordinator_missing_entry(hass: HomeAssistant) -> None:
    """Test _refresh_coordinator handles a non-existent entry gracefully."""
    # Must not raise -- logs a warning instead
    await _refresh_coordinator(hass, "nonexistent_entry_id")


async def test_refresh_coordinator_no_runtime_data(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test _refresh_coordinator handles missing runtime_data gracefully."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    # Do NOT set up the entry -- runtime_data is not set

    # Must not raise -- logs a warning instead
    await _refresh_coordinator(hass, "test_entry")


async def test_refresh_all_coordinators_no_entries(hass: HomeAssistant) -> None:
    """Test _refresh_all_coordinators does nothing when no entries exist."""
    # Must not raise
    await _refresh_all_coordinators(hass)


# ------------------------------------------------------------------
# Gas energy conversion & cost calculation
# ------------------------------------------------------------------


async def test_gas_m3_to_kwh_conversion(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that gas consumption in m3 is correctly converted to kWh.

    Formula: kWh = m3 * Brennwert * Zustandszahl
    With mock data: 14.8 m3 * 11.465 * 0.9684 = 164.224 kWh (approx.)
    """
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data.consumption is not None

    # Manual calculation: 14.8 * 11.465 * 0.9684
    expected_kwh = 14.8 * 11.465 * 0.9684
    assert data.energy_consumption is not None
    assert abs(data.energy_consumption - round(expected_kwh, 3)) < 0.01


async def test_gas_cost_calculation_ct_per_kwh(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test gas cost: kWh * price(ct/kWh) / 100 = EUR.

    With mock data:
      consumption = 14.8 m3
      Brennwert = 11.465, Zustandszahl = 0.9684
      kWh = 14.8 * 11.465 * 0.9684 = ~164.224
      price = 1.85 ct/kWh
      cost = 164.224 * 1.85 / 100 = ~3.04 EUR
    """
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    kwh = 14.8 * 11.465 * 0.9684
    expected_cost = round(kwh * 1.85 / 100.0, 2)

    assert data.last_period_cost is not None
    assert data.last_period_cost == expected_cost


async def test_gas_projected_costs_use_energy_conversion(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that monthly/yearly projected costs for gas use the kWh conversion.

    projected_cost = monthly_projection_m3 * Brennwert * Zustandszahl * price(ct/kWh) / 100
    """
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data.monthly_projection is not None
    assert data.yearly_projection is not None
    assert data.current_price is not None

    bw = 11.465
    zz = 0.9684
    price = data.current_price  # 1.85 ct/kWh

    expected_monthly_cost = round(data.monthly_projection * bw * zz * price / 100.0, 2)
    expected_yearly_cost = round(data.yearly_projection * bw * zz * price / 100.0, 2)

    assert data.monthly_projected_cost == expected_monthly_cost
    assert data.yearly_projected_cost == expected_yearly_cost


async def test_gas_custom_conversion_factors(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test gas calculation with non-default Brennwert and Zustandszahl."""
    custom_config = {
        **MOCK_GAS_CONFIG,
        "calorific_value": 10.5,
        "condition_factor": 0.95,
    }

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=custom_config,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Conversion factors should reflect custom values
    assert data.calorific_value == 10.5
    assert data.condition_factor == 0.95

    # Energy: 14.8 * 10.5 * 0.95 = 147.63
    expected_kwh = 14.8 * 10.5 * 0.95
    assert data.energy_consumption is not None
    assert abs(data.energy_consumption - round(expected_kwh, 3)) < 0.01

    # Cost: 147.63 * 1.85 / 100 = 2.73 EUR
    expected_cost = round(expected_kwh * 1.85 / 100.0, 2)
    assert data.last_period_cost == expected_cost


async def test_gas_single_reading_no_energy(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that a gas meter with only one reading has no energy_consumption."""
    db = mock_db_empty
    await db.async_add_reading(
        entry_id="test_entry",
        meter_number="GAS-12345",
        reading=100.0,
        timestamp="2026-01-01T10:00:00+00:00",
    )

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data.reading == 100.0
    assert data.consumption is None
    assert data.energy_consumption is None


# ------------------------------------------------------------------
# Water cost calculation (EUR/m³, no energy conversion)
# ------------------------------------------------------------------


async def test_water_cost_calculation_eur_per_m3(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test water cost: m3 * price(EUR/m3) = EUR.

    Water uses simple volume-based pricing without energy conversion.
    """
    db = mock_db_empty

    # Add readings for water meter
    for r in [
        ("WAT-67890", 200.0, "2026-01-01T10:00:00+00:00"),
        ("WAT-67890", 215.0, "2026-01-15T10:00:00+00:00"),
        ("WAT-67890", 235.5, "2026-02-01T10:00:00+00:00"),
    ]:
        await db.async_add_reading(
            entry_id="test_water",
            meter_number=r[0],
            reading=r[1],
            timestamp=r[2],
        )

    # Add price: 2.50 EUR/m³
    await db.async_add_price(
        entry_id="test_water",
        price_per_unit=2.50,
        valid_from="2026-01-01",
        currency="EUR",
    )

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_WAT-67890",
        entry_id="test_water",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Consumption: 235.5 - 215.0 = 20.5 m³
    assert data.consumption is not None
    assert abs(data.consumption - 20.5) < 0.001

    # Water has NO energy conversion
    assert data.energy_consumption is None
    assert data.calorific_value is None
    assert data.condition_factor is None

    # Cost: 20.5 * 2.50 = 51.25 EUR
    assert data.current_price == 2.50
    assert data.last_period_cost is not None
    expected_cost = round(20.5 * 2.50, 2)
    assert data.last_period_cost == expected_cost


async def test_water_projected_costs_simple_multiplication(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that water projected costs use simple m3 * EUR/m3 without energy conversion."""
    db = mock_db_empty

    for r in [
        ("WAT-67890", 200.0, "2026-01-01T10:00:00+00:00"),
        ("WAT-67890", 215.0, "2026-01-15T10:00:00+00:00"),
        ("WAT-67890", 235.5, "2026-02-01T10:00:00+00:00"),
    ]:
        await db.async_add_reading(
            entry_id="test_water",
            meter_number=r[0],
            reading=r[1],
            timestamp=r[2],
        )

    await db.async_add_price(
        entry_id="test_water",
        price_per_unit=2.50,
        valid_from="2026-01-01",
        currency="EUR",
    )

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_WAT-67890",
        entry_id="test_water",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data.monthly_projection is not None
    assert data.yearly_projection is not None

    # Water projected costs: simple m3 * EUR/m3
    expected_monthly_cost = round(data.monthly_projection * 2.50, 2)
    expected_yearly_cost = round(data.yearly_projection * 2.50, 2)

    assert data.monthly_projected_cost == expected_monthly_cost
    assert data.yearly_projected_cost == expected_yearly_cost


# ------------------------------------------------------------------
# Gas vs. Water cost comparison
# ------------------------------------------------------------------


async def test_gas_and_water_cost_formulas_differ(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Verify that gas and water apply fundamentally different cost formulas.

    Given the same consumption (10 m3) and price (5.0):
      Gas:   kWh = 10 * 11.465 * 0.9684 = ~111.03; cost = 111.03 * 5.0 / 100 = ~5.55 EUR
      Water: cost = 10 * 5.0 = 50.00 EUR
    """
    db = mock_db_empty

    # --- Gas meter ---
    for ts, val in [
        ("2026-01-01T10:00:00+00:00", 100.0),
        ("2026-02-01T10:00:00+00:00", 110.0),
    ]:
        await db.async_add_reading(entry_id="gas_entry", meter_number="G-1", reading=val, timestamp=ts)
    await db.async_add_price(entry_id="gas_entry", price_per_unit=5.0, valid_from="2026-01-01", currency="EUR")

    gas_entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_G-1",
        entry_id="gas_entry",
    )
    gas_entry.add_to_hass(hass)

    gas_coord = MeterCoordinator(hass, gas_entry, db)
    await gas_coord.async_refresh()

    # --- Water meter ---
    for ts, val in [
        ("2026-01-01T10:00:00+00:00", 100.0),
        ("2026-02-01T10:00:00+00:00", 110.0),
    ]:
        await db.async_add_reading(entry_id="water_entry", meter_number="W-1", reading=val, timestamp=ts)
    await db.async_add_price(entry_id="water_entry", price_per_unit=5.0, valid_from="2026-01-01", currency="EUR")

    water_entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_W-1",
        entry_id="water_entry",
    )
    water_entry.add_to_hass(hass)

    water_coord = MeterCoordinator(hass, water_entry, db)
    await water_coord.async_refresh()

    gas = gas_coord.data
    water = water_coord.data
    assert gas is not None
    assert water is not None

    # Same consumption
    assert gas.consumption == water.consumption == 10.0

    # Gas has energy_consumption, water does not
    assert gas.energy_consumption is not None
    assert water.energy_consumption is None

    # Different cost formulas produce different results
    assert gas.last_period_cost is not None
    assert water.last_period_cost is not None
    assert gas.last_period_cost != water.last_period_cost

    # Verify exact gas cost: kWh * price / 100
    gas_kwh = 10.0 * 11.465 * 0.9684
    expected_gas_cost = round(gas_kwh * 5.0 / 100.0, 2)
    assert gas.last_period_cost == expected_gas_cost

    # Verify exact water cost: m3 * price
    expected_water_cost = round(10.0 * 5.0, 2)
    assert water.last_period_cost == expected_water_cost


# ------------------------------------------------------------------
# Meter number change -- consumption resets
# ------------------------------------------------------------------


async def test_meter_change_resets_consumption(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """When the meter number changes, consumption and energy must be None.

    Old meter: GAS-12345 readings 100 -> 150
    New meter: GAS-99999 reading  10
    The last two entries have different meter numbers, so no delta.
    """
    db = mock_db_empty

    await db.async_add_reading("e1", "GAS-12345", 100.0, "2026-01-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-12345", 150.0, "2026-02-01T10:00:00+00:00")
    # Meter replaced
    await db.async_add_reading("e1", "GAS-99999", 10.0, "2026-03-01T10:00:00+00:00")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="e1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Latest reading is from new meter
    assert data.reading == 10.0
    assert data.meter_number == "GAS-99999"

    # No consumption -- meter numbers differ between last two entries
    assert data.consumption is None
    assert data.days_between is None
    assert data.energy_consumption is None

    # No cost for last period either
    assert data.last_period_cost is None


async def test_meter_change_projection_uses_new_meter(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Projection after meter change is based only on the new meter's readings.

    Old meter: GAS-12345  100 -> 150  (ignored for projection)
    New meter: GAS-99999  10 -> 30    (20 m3 in 31 days)
    """
    db = mock_db_empty

    await db.async_add_reading("e1", "GAS-12345", 100.0, "2026-01-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-12345", 150.0, "2026-02-01T10:00:00+00:00")
    # Meter replaced
    await db.async_add_reading("e1", "GAS-99999", 10.0, "2026-03-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-99999", 30.0, "2026-04-01T10:00:00+00:00")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="e1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Consumption: 30 - 10 = 20 (same meter for last two entries)
    assert data.consumption is not None
    assert abs(data.consumption - 20.0) < 0.001

    # Projection is based only on the new meter (10 -> 30 over 31 days)
    assert data.daily_average is not None
    expected_avg = round(20.0 / 31.0, 4)
    assert abs(data.daily_average - expected_avg) < 0.001

    # Monthly projection from new meter only
    expected_monthly = round(expected_avg * DAYS_PER_MONTH, 3)
    assert data.monthly_projection is not None
    assert abs(data.monthly_projection - expected_monthly) < 0.1


async def test_meter_change_single_new_reading_no_projection(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """With only one reading on the new meter, no projection is possible.

    Old meter: GAS-12345  100 -> 150
    New meter: GAS-99999  10  (only one reading)
    """
    db = mock_db_empty

    await db.async_add_reading("e1", "GAS-12345", 100.0, "2026-01-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-12345", 150.0, "2026-02-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-99999", 10.0, "2026-03-01T10:00:00+00:00")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="e1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # No projection with only one reading on the new meter
    assert data.daily_average is None
    assert data.monthly_projection is None
    assert data.yearly_projection is None


async def test_water_meter_change_resets_consumption(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Water meter change also resets consumption (no delta across meters)."""
    db = mock_db_empty

    await db.async_add_reading("w1", "WAT-001", 200.0, "2026-01-01T10:00:00+00:00")
    await db.async_add_reading("w1", "WAT-001", 250.0, "2026-02-01T10:00:00+00:00")
    await db.async_add_reading("w1", "WAT-002", 5.0, "2026-03-01T10:00:00+00:00")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_WAT-001",
        entry_id="w1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    assert data.reading == 5.0
    assert data.meter_number == "WAT-002"
    assert data.consumption is None
    assert data.days_between is None
    assert data.energy_consumption is None


async def test_meter_change_cost_not_computed(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """After a meter change with no consumption, last_period_cost must be None."""
    db = mock_db_empty

    await db.async_add_reading("e1", "GAS-12345", 100.0, "2026-01-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-12345", 150.0, "2026-02-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-99999", 10.0, "2026-03-01T10:00:00+00:00")

    await db.async_add_price("e1", 1.85, "2026-01-01", currency="EUR")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="e1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # Price exists and is current
    assert data.current_price == 1.85

    # But no cost because consumption is None (meter changed)
    assert data.last_period_cost is None

    # No projected costs either (only 1 reading on new meter)
    assert data.monthly_projected_cost is None
    assert data.yearly_projected_cost is None


# ---------------------------------------------------------------------------
# Energy Dashboard statistics import tests
# ---------------------------------------------------------------------------


async def test_statistics_imported_with_reading_timestamps(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Statistics use the actual reading date, not the date of entry."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
        title="Gas Meter - Kitchen",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, mock_db)
        await coordinator.async_refresh()

        assert mock_import.called
        call_args = mock_import.call_args
        _hass_arg, metadata, stats_iter = call_args[0]
        stats = list(stats_iter) if not isinstance(stats_iter, list) else stats_iter

        # Metadata
        assert metadata["source"] == "gas_water_meter"
        assert metadata["statistic_id"] == "gas_water_meter:reading_test_entry"
        assert metadata["has_sum"] is True
        assert metadata["has_mean"] is False
        assert metadata["name"] == "Gas Meter - Kitchen"

        # 3 readings → 3 statistics entries
        assert len(stats) == 3

        # Verify timestamps match reading dates (start of hour)
        expected_starts = [
            datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC),
            datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
            datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC),
        ]
        for stat, expected in zip(stats, expected_starts, strict=True):
            assert stat["start"] == expected

        # state = raw meter reading
        assert stats[0]["state"] == 100.0
        assert stats[1]["state"] == 110.5
        assert stats[2]["state"] == 125.3

        # sum = cumulative consumption since first reading
        assert stats[0]["sum"] == 0.0  # first: no prior consumption
        assert stats[1]["sum"] == 10.5  # 110.5 - 100.0
        assert stats[2]["sum"] == 25.3  # 10.5 + (125.3 - 110.5)


async def test_statistics_handles_meter_number_change(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Meter replacement resets delta but running sum continues."""
    db = mock_db_empty
    # Old meter readings
    await db.async_add_reading("e1", "GAS-OLD", 100.0, "2025-01-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-OLD", 150.0, "2025-06-01T10:00:00+00:00")
    # New meter starts at 0
    await db.async_add_reading("e1", "GAS-NEW", 0.0, "2025-07-01T10:00:00+00:00")
    await db.async_add_reading("e1", "GAS-NEW", 30.0, "2025-12-01T10:00:00+00:00")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data={**MOCK_GAS_CONFIG, "meter_number": "GAS-NEW"},
        unique_id="gas_water_meter_gas_GAS-NEW",
        entry_id="e1",
        title="Gas Meter",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, db)
        await coordinator.async_refresh()

        call_args = mock_import.call_args
        stats = list(call_args[0][2])

        assert len(stats) == 4

        # Old meter: 100 → 150 = 50 m³ consumption
        assert stats[0]["sum"] == 0.0  # first reading
        assert stats[1]["sum"] == 50.0  # 150 - 100

        # Meter change: no consumption counted (different meter_number)
        assert stats[2]["sum"] == 50.0  # unchanged (meter changed)

        # New meter: 0 → 30 = 30 m³ consumption, total = 50 + 30
        assert stats[3]["sum"] == 80.0  # 50 + 30


async def test_statistics_change_detection_skips_reimport(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Second refresh with unchanged data does not re-import statistics."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
        title="Gas Meter",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, mock_db)

        # First refresh → import happens
        await coordinator.async_refresh()
        assert mock_import.call_count == 1

        # Second refresh, same data → no re-import
        await coordinator.async_refresh()
        assert mock_import.call_count == 1


async def test_statistics_reimported_after_new_reading(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Adding a new reading triggers a re-import of statistics."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
        title="Gas Meter",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, mock_db)
        await coordinator.async_refresh()
        assert mock_import.call_count == 1

        # Add a new reading
        await mock_db.async_add_reading("test_entry", "GAS-12345", 140.0, "2026-03-01T10:00:00+00:00")

        # Refresh again → re-import with 4 readings
        await coordinator.async_refresh()
        assert mock_import.call_count == 2

        stats = list(mock_import.call_args[0][2])
        assert len(stats) == 4
        # New sum: 10.5 + 14.8 + 14.7 = 40.0
        assert stats[3]["sum"] == 40.0


async def test_statistics_empty_readings_no_import(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """No statistics import when there are no readings."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
        title="Gas Meter",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, mock_db_empty)
        await coordinator.async_refresh()

        assert not mock_import.called


async def test_statistics_hourly_deduplication(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Two readings in the same hour produce only one statistics entry."""
    db = mock_db_empty
    # Two readings within the same hour (10:00 - 10:59)
    await db.async_add_reading("e1", "GAS-12345", 100.0, "2026-01-01T10:15:00+00:00")
    await db.async_add_reading("e1", "GAS-12345", 105.0, "2026-01-01T10:45:00+00:00")
    # One reading in the next hour
    await db.async_add_reading("e1", "GAS-12345", 110.0, "2026-01-01T11:30:00+00:00")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="e1",
        title="Gas Meter",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, db)
        await coordinator.async_refresh()

        stats = list(mock_import.call_args[0][2])

        # Two hours → 2 entries (first hour deduplicated)
        assert len(stats) == 2

        # Hour 10: later reading (105.0) wins
        assert stats[0]["start"] == datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
        assert stats[0]["state"] == 105.0
        assert stats[0]["sum"] == 5.0  # 100 → 105

        # Hour 11
        assert stats[1]["start"] == datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC)
        assert stats[1]["state"] == 110.0
        assert stats[1]["sum"] == 10.0  # 5 + (110 - 105)


async def test_statistics_water_meter(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Water meter statistics use m³ unit and correct source."""
    db = mock_db_empty
    await db.async_add_reading("w1", "WAT-67890", 50.0, "2026-01-01T08:00:00+00:00")
    await db.async_add_reading("w1", "WAT-67890", 60.0, "2026-02-01T08:00:00+00:00")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_WAT-67890",
        entry_id="w1",
        title="Water Meter - Garden",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, db)
        await coordinator.async_refresh()

        call_args = mock_import.call_args
        metadata = call_args[0][1]
        stats = list(call_args[0][2])

        assert metadata["source"] == "gas_water_meter"
        assert metadata["statistic_id"] == "gas_water_meter:reading_w1"
        assert metadata["name"] == "Water Meter - Garden"
        assert metadata["unit_of_measurement"] == "m³"

        assert len(stats) == 2
        assert stats[0]["sum"] == 0.0
        assert stats[1]["sum"] == 10.0


async def test_statistics_negative_delta_ignored(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Negative consumption (data entry error) is treated as zero."""
    db = mock_db_empty
    await db.async_add_reading("e1", "GAS-12345", 100.0, "2026-01-01T10:00:00+00:00")
    # Erroneous lower reading
    await db.async_add_reading("e1", "GAS-12345", 95.0, "2026-02-01T10:00:00+00:00")
    # Corrected reading
    await db.async_add_reading("e1", "GAS-12345", 120.0, "2026-03-01T10:00:00+00:00")

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="e1",
        title="Gas Meter",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, db)
        await coordinator.async_refresh()

        stats = list(mock_import.call_args[0][2])

        assert len(stats) == 3
        assert stats[0]["sum"] == 0.0
        # 95 - 100 = -5 → ignored, sum stays 0
        assert stats[1]["sum"] == 0.0
        # 120 - 95 = 25 → added
        assert stats[2]["sum"] == 25.0


async def test_base_fee_prorated_in_last_period_cost(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that base_fee is prorated and added to last_period_cost.

    Formula: last_period_cost = consumption_cost + base_fee * days / DAYS_PER_YEAR
    With: consumption 10 m³, price 5.0 EUR/m³, base_fee 365.25 EUR, 31 days
    => water cost = 10 * 5 = 50.00
    => prorated base fee = 365.25 * 31 / 365.25 = 31.00
    => total = 81.00
    """
    db = mock_db_empty

    for ts, val in [
        ("2026-01-01T10:00:00+00:00", 100.0),
        ("2026-02-01T10:00:00+00:00", 110.0),
    ]:
        await db.async_add_reading(entry_id="w1", meter_number="W-1", reading=val, timestamp=ts)

    await db.async_add_price(
        entry_id="w1",
        price_per_unit=5.0,
        valid_from="2026-01-01",
        currency="EUR",
        base_fee=365.25,
    )

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_W-1",
        entry_id="w1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data.consumption == 10.0
    assert data.days_between is not None
    assert abs(data.days_between - 31.0) < 0.1

    # consumption_cost = 10 * 5 = 50.00
    # prorated base fee = 365.25 * 31 / 365.25 = 31.00
    expected = round(50.0 + 31.0, 2)
    assert data.last_period_cost == expected


async def test_base_fee_in_monthly_projected_cost(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that base_fee is prorated for monthly projected cost."""
    db = mock_db_empty

    for ts, val in [
        ("2026-01-01T10:00:00+00:00", 100.0),
        ("2026-02-01T10:00:00+00:00", 110.0),
        ("2026-03-01T10:00:00+00:00", 125.0),
    ]:
        await db.async_add_reading(entry_id="w1", meter_number="W-1", reading=val, timestamp=ts)

    await db.async_add_price(
        entry_id="w1",
        price_per_unit=2.50,
        valid_from="2026-01-01",
        currency="EUR",
        base_fee=120.0,
    )

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_W-1",
        entry_id="w1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data.monthly_projection is not None

    # Monthly consumption cost
    consumption_cost = round(data.monthly_projection * 2.50, 2)
    # Prorated base fee for one month
    prorated = round(120.0 * DAYS_PER_MONTH / DAYS_PER_YEAR, 2)
    expected = round(consumption_cost + prorated, 2)
    assert data.monthly_projected_cost == expected


async def test_base_fee_in_yearly_projected_cost(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that full base_fee is added to yearly projected cost."""
    db = mock_db_empty

    for ts, val in [
        ("2026-01-01T10:00:00+00:00", 100.0),
        ("2026-02-01T10:00:00+00:00", 110.0),
        ("2026-03-01T10:00:00+00:00", 125.0),
    ]:
        await db.async_add_reading(entry_id="w1", meter_number="W-1", reading=val, timestamp=ts)

    await db.async_add_price(
        entry_id="w1",
        price_per_unit=2.50,
        valid_from="2026-01-01",
        currency="EUR",
        base_fee=120.0,
    )

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_W-1",
        entry_id="w1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data.yearly_projection is not None

    # Yearly consumption cost
    consumption_cost = round(data.yearly_projection * 2.50, 2)
    # Full base fee for the year
    expected = round(consumption_cost + 120.0, 2)
    assert data.yearly_projected_cost == expected


async def test_base_fee_none_backwards_compatible(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that base_fee=None (legacy data) does not change cost calculations."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, mock_db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None

    # current_base_fee should be None (no base_fee in mock data)
    assert data.current_base_fee is None

    # Costs should be purely consumption-based (no base fee added)
    kwh = 14.8 * 11.465 * 0.9684
    expected_cost = round(kwh * 1.85 / 100.0, 2)
    assert data.last_period_cost == expected_cost


async def test_current_base_fee_sensor_value(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that current_base_fee is set from the current price entry."""
    db = mock_db_empty
    await db.async_add_reading(entry_id="w1", meter_number="W-1", reading=100.0, timestamp="2026-01-01T10:00:00+00:00")
    await db.async_add_price(
        entry_id="w1",
        price_per_unit=2.50,
        valid_from="2026-01-01",
        currency="EUR",
        base_fee=96.50,
    )

    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_WATER_CONFIG,
        unique_id="gas_water_meter_water_W-1",
        entry_id="w1",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry, db)
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data.current_base_fee == 96.50


async def test_statistics_uses_entry_title(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Statistics name uses the config entry title (user-editable)."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
        title="Mein Gaszähler Küche",
    )
    entry.add_to_hass(hass)

    with patch("homeassistant.components.recorder.statistics.async_import_statistics") as mock_import:
        coordinator = MeterCoordinator(hass, entry, mock_db)
        await coordinator.async_refresh()

        metadata = mock_import.call_args[0][1]
        assert metadata["name"] == "Mein Gaszähler Küche"

"""Tests for the Gas & Water Meter coordinator (projection + cost logic)."""

from __future__ import annotations

from datetime import timedelta

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

from .conftest import MOCK_GAS_CONFIG

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
    """Test cost calculations."""
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

    # Current price should be 1.85 (valid from 2026-01-01)
    assert data.current_price == 1.85

    # Last period cost: consumption (14.8) * price at prev reading date
    # Previous reading is 2026-01-15, price at that date is 1.85
    assert data.last_period_cost is not None
    expected_cost = 14.8 * 1.85
    assert abs(data.last_period_cost - round(expected_cost, 2)) < 0.01

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


async def test_coordinator_reflects_new_data_after_refresh(
    hass: HomeAssistant, mock_db_empty: MeterDatabase
) -> None:
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

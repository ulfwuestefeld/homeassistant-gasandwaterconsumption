"""Tests for the Gas & Water Meter coordinator (projection + cost logic)."""

from __future__ import annotations

from unittest.mock import patch

from custom_components.gas_water_meter.const import DAYS_PER_MONTH, DAYS_PER_YEAR
from custom_components.gas_water_meter.coordinator import MeterCoordinator, _days_between
from homeassistant.core import HomeAssistant

from .conftest import MOCK_GAS_CONFIG, MOCK_STORE_DATA

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


async def test_coordinator_computes_core_data(hass: HomeAssistant, mock_store_load, mock_store_save) -> None:
    """Test that coordinator computes core sensor values correctly."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

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


async def test_coordinator_computes_projection(hass: HomeAssistant, mock_store_load, mock_store_save) -> None:
    """Test projection calculations."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    data = coordinator.data
    assert data is not None

    # Total consumption: 125.3 - 100.0 = 25.3
    # Total days: Jan 1 to Feb 1 = 31 days
    # Daily average: 25.3 / 31 ≈ 0.8161
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


async def test_coordinator_computes_costs(hass: HomeAssistant, mock_store_load, mock_store_save) -> None:
    """Test cost calculations."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

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


async def test_coordinator_empty_store(hass: HomeAssistant, mock_store_empty, mock_store_save) -> None:
    """Test coordinator with no readings."""
    entry = MockConfigEntry(
        domain="gas_water_meter",
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    coordinator = MeterCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

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


async def test_coordinator_single_reading(hass: HomeAssistant, mock_store_save) -> None:
    """Test coordinator with only one reading (no delta/projection possible)."""
    single_reading_data = {
        **MOCK_STORE_DATA,
        "readings": [MOCK_STORE_DATA["readings"][0]],
        "prices": [],
    }

    with patch(
        "custom_components.gas_water_meter.store.Store.async_load",
        return_value=single_reading_data,
    ):
        entry = MockConfigEntry(
            domain="gas_water_meter",
            data=MOCK_GAS_CONFIG,
            unique_id="gas_water_meter_gas_GAS-12345",
        )
        entry.add_to_hass(hass)

        coordinator = MeterCoordinator(hass, entry)
        await coordinator.async_setup()
        await coordinator.async_config_entry_first_refresh()

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

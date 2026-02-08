"""Tests for the Gas & Water Meter persistent storage."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from custom_components.gas_water_meter.store import MeterStore
from homeassistant.core import HomeAssistant

from .conftest import MOCK_STORE_DATA


async def test_load_existing_data(hass: HomeAssistant) -> None:
    """Test loading existing data from storage."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=MOCK_STORE_DATA,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        store = MeterStore(hass, "test_entry_id")
        data = await store.async_load("gas", "Kitchen", "GAS-12345", "EUR")

    assert data["meter_type"] == "gas"
    assert data["meter_name"] == "Kitchen"
    assert len(data["readings"]) == 3
    assert len(data["prices"]) == 2


async def test_load_empty_store(hass: HomeAssistant) -> None:
    """Test loading from empty storage creates defaults."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=None,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ) as mock_save,
    ):
        store = MeterStore(hass, "test_entry_id")
        data = await store.async_load("water", "Garden", "WAT-67890", "CHF")

    assert data["meter_type"] == "water"
    assert data["meter_name"] == "Garden"
    assert data["meter_number"] == "WAT-67890"
    assert data["currency"] == "CHF"
    assert data["readings"] == []
    assert data["prices"] == []
    # Should save the initial data
    mock_save.assert_called_once()


async def test_add_reading(hass: HomeAssistant) -> None:
    """Test adding a meter reading."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=None,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        store = MeterStore(hass, "test_entry_id")
        await store.async_load("gas", "Kitchen", "GAS-12345", "EUR")

        await store.async_add_reading(
            reading=100.5,
            meter_number="GAS-12345",
            timestamp="2026-02-01T10:00:00+00:00",
            image_path=None,
        )

    assert len(store.readings) == 1
    assert store.readings[0]["reading"] == 100.5
    assert store.readings[0]["meter_number"] == "GAS-12345"


async def test_readings_sorted_by_timestamp(hass: HomeAssistant) -> None:
    """Test that readings are kept sorted by timestamp."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=None,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        store = MeterStore(hass, "test_entry_id")
        await store.async_load("gas", "Kitchen", "GAS-12345", "EUR")

        # Add readings out of order
        await store.async_add_reading(200.0, "GAS-12345", "2026-03-01T10:00:00+00:00")
        await store.async_add_reading(100.0, "GAS-12345", "2026-01-01T10:00:00+00:00")
        await store.async_add_reading(150.0, "GAS-12345", "2026-02-01T10:00:00+00:00")

    assert store.readings[0]["reading"] == 100.0
    assert store.readings[1]["reading"] == 150.0
    assert store.readings[2]["reading"] == 200.0


async def test_add_price(hass: HomeAssistant) -> None:
    """Test adding a price entry."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=None,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        store = MeterStore(hass, "test_entry_id")
        await store.async_load("gas", "Kitchen", "GAS-12345", "EUR")

        await store.async_add_price(1.85, "2026-01-01", "EUR")

    assert len(store.prices) == 1
    assert store.prices[0]["price_per_unit"] == 1.85


async def test_get_last_and_previous_reading(hass: HomeAssistant) -> None:
    """Test getting last and previous readings."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=MOCK_STORE_DATA,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        store = MeterStore(hass, "test_entry_id")
        await store.async_load("gas", "Kitchen", "GAS-12345", "EUR")

    last = store.get_last_reading()
    assert last is not None
    assert last["reading"] == 125.3

    prev = store.get_previous_reading()
    assert prev is not None
    assert prev["reading"] == 110.5

    first = store.get_first_reading()
    assert first is not None
    assert first["reading"] == 100.0


async def test_get_current_price(hass: HomeAssistant) -> None:
    """Test getting the current active price."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=MOCK_STORE_DATA,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        store = MeterStore(hass, "test_entry_id")
        await store.async_load("gas", "Kitchen", "GAS-12345", "EUR")

    current = store.get_current_price()
    assert current is not None
    assert current["price_per_unit"] == 1.85


async def test_get_price_at_date(hass: HomeAssistant) -> None:
    """Test getting the price valid at a specific date."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=MOCK_STORE_DATA,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        store = MeterStore(hass, "test_entry_id")
        await store.async_load("gas", "Kitchen", "GAS-12345", "EUR")

    # Before 2026: should get 2025 price
    price = store.get_price_at("2025-06-15")
    assert price is not None
    assert price["price_per_unit"] == 1.50

    # After 2026-01-01: should get 2026 price
    price = store.get_price_at("2026-02-01T10:00:00+00:00")
    assert price is not None
    assert price["price_per_unit"] == 1.85


async def test_no_readings_returns_none(hass: HomeAssistant) -> None:
    """Test that empty store returns None for readings."""
    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_load",
            return_value=None,
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        store = MeterStore(hass, "test_entry_id")
        await store.async_load("gas", "Kitchen", "GAS-12345", "EUR")

    assert store.get_last_reading() is None
    assert store.get_previous_reading() is None
    assert store.get_first_reading() is None
    assert store.get_current_price() is None


async def test_store_not_loaded_raises(hass: HomeAssistant) -> None:
    """Test that operations on unloaded store raise RuntimeError."""
    store = MeterStore(hass, "test_entry_id")

    with pytest.raises(RuntimeError, match="Store not loaded"):
        await store.async_add_reading(100.0, "GAS-12345", "2026-01-01T10:00:00+00:00")

    with pytest.raises(RuntimeError, match="Store not loaded"):
        await store.async_add_price(1.85, "2026-01-01", "EUR")

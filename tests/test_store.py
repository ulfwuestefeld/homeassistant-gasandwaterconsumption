"""Tests for the Gas & Water Meter legacy JSON storage layer."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.gas_water_meter.store import MeterStore
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config = MagicMock()
    hass.config.path = MagicMock(side_effect=lambda *args: os.path.join(tempfile.gettempdir(), *args))
    hass.data = {}  # Add data dict for Store compatibility
    hass.async_add_executor_job = MagicMock()

    # Mock async_add_executor_job to run the function synchronously
    async def mock_executor(func, *args):
        return func(*args) if callable(func) else func

    hass.async_add_executor_job = MagicMock(side_effect=mock_executor)
    return hass


class TestMeterStoreInitialization:
    """Tests for MeterStore initialization."""

    def test_init_creates_store(self, mock_hass: MagicMock) -> None:
        """Test that initialization creates a store instance."""
        store = MeterStore(mock_hass, "test_entry")

        assert store._entry_id == "test_entry"
        assert store._hass == mock_hass
        assert store._data is None

    def test_data_property_returns_none_initially(self, mock_hass: MagicMock) -> None:
        """Test that data property returns None before loading."""
        store = MeterStore(mock_hass, "test_entry")
        assert store.data is None

    def test_readings_property_returns_empty_list_initially(self, mock_hass: MagicMock) -> None:
        """Test that readings property returns empty list when not loaded."""
        store = MeterStore(mock_hass, "test_entry")
        assert store.readings == []

    def test_prices_property_returns_empty_list_initially(self, mock_hass: MagicMock) -> None:
        """Test that prices property returns empty list when not loaded."""
        store = MeterStore(mock_hass, "test_entry")
        assert store.prices == []


class TestMeterStoreLoad:
    """Tests for loading data."""

    @pytest.mark.asyncio
    async def test_async_load_creates_default_data(self, mock_hass: MagicMock) -> None:
        """Test that async_load creates default data structure when no data exists."""
        with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
            mock_store_instance = MagicMock()
            mock_store_instance.async_load = AsyncMock(return_value=None)
            mock_store_instance.async_save = AsyncMock()
            mock_store_class.return_value = mock_store_instance

            store = MeterStore(mock_hass, "test_entry")
            data = await store.async_load(
                meter_type="gas",
                meter_name="Kitchen",
                meter_number="GAS-12345",
                currency="EUR",
            )

            assert data["meter_type"] == "gas"
            assert data["meter_name"] == "Kitchen"
            assert data["meter_number"] == "GAS-12345"
            assert data["currency"] == "EUR"
            assert data["readings"] == []
            assert data["prices"] == []
            mock_store_instance.async_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_load_restores_existing_data(self, mock_hass: MagicMock) -> None:
        """Test that async_load restores existing stored data."""
        existing_data = {
            "meter_type": "water",
            "meter_name": "Bathroom",
            "meter_number": "WAT-67890",
            "currency": "USD",
            "readings": [
                {
                    "meter_number": "WAT-67890",
                    "reading": 100.0,
                    "timestamp": "2026-01-01T10:00:00+00:00",
                    "image_path": None,
                }
            ],
            "prices": [
                {
                    "price_per_unit": 2.5,
                    "valid_from": "2026-01-01",
                    "currency": "USD",
                }
            ],
        }

        with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
            mock_store_instance = MagicMock()
            mock_store_instance.async_load = AsyncMock(return_value=existing_data)
            mock_store_class.return_value = mock_store_instance

            store = MeterStore(mock_hass, "test_entry")
            data = await store.async_load(
                meter_type="gas",  # Different type, should be overridden
                meter_name="Kitchen",
                meter_number="GAS-12345",
                currency="EUR",
            )

            assert data["meter_type"] == "water"
            assert data["meter_name"] == "Bathroom"
            assert len(data["readings"]) == 1
            assert len(data["prices"]) == 1


class TestMeterStoreReadings:
    """Tests for reading operations."""

    @pytest.mark.asyncio
    async def test_async_add_reading(self, mock_hass: MagicMock) -> None:
        """Test adding a reading."""
        with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
            mock_store_instance = MagicMock()
            mock_store_instance.async_load = AsyncMock(return_value=None)
            mock_store_instance.async_save = AsyncMock()
            mock_store_class.return_value = mock_store_instance

            store = MeterStore(mock_hass, "test_entry")
            await store.async_load(
                meter_type="gas",
                meter_name="Kitchen",
                meter_number="GAS-12345",
                currency="EUR",
            )

            await store.async_add_reading(
                reading=100.0,
                meter_number="GAS-12345",
                timestamp="2026-01-01T10:00:00+00:00",
            )

            assert len(store.readings) == 1
            assert store.readings[0]["reading"] == 100.0
            assert store.readings[0]["meter_number"] == "GAS-12345"

    @pytest.mark.asyncio
    async def test_async_add_reading_with_image_path(self, mock_hass: MagicMock) -> None:
        """Test adding a reading with an image path."""
        with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
            mock_store_instance = MagicMock()
            mock_store_instance.async_load = AsyncMock(return_value=None)
            mock_store_instance.async_save = AsyncMock()
            mock_store_class.return_value = mock_store_instance

            store = MeterStore(mock_hass, "test_entry")
            await store.async_load(
                meter_type="gas",
                meter_name="Kitchen",
                meter_number="GAS-12345",
                currency="EUR",
            )

            await store.async_add_reading(
                reading=100.0,
                meter_number="GAS-12345",
                timestamp="2026-01-01T10:00:00+00:00",
                image_path="/config/media/gas_water_meter/photo.jpg",
            )

            assert store.readings[0]["image_path"] == "/config/media/gas_water_meter/photo.jpg"

    @pytest.mark.asyncio
    async def test_readings_sorted_by_timestamp(self, mock_hass: MagicMock) -> None:
        """Test that readings are sorted by timestamp."""
        with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
            mock_store_instance = MagicMock()
            mock_store_instance.async_load = AsyncMock(return_value=None)
            mock_store_instance.async_save = AsyncMock()
            mock_store_class.return_value = mock_store_instance

            store = MeterStore(mock_hass, "test_entry")
            await store.async_load(
                meter_type="gas",
                meter_name="Kitchen",
                meter_number="GAS-12345",
                currency="EUR",
            )

            # Add readings out of order
            await store.async_add_reading(
                reading=110.0,
                meter_number="GAS-12345",
                timestamp="2026-01-15T10:00:00+00:00",
            )
            await store.async_add_reading(
                reading=100.0,
                meter_number="GAS-12345",
                timestamp="2026-01-01T10:00:00+00:00",
            )
            await store.async_add_reading(
                reading=105.0,
                meter_number="GAS-12345",
                timestamp="2026-01-08T10:00:00+00:00",
            )

            assert len(store.readings) == 3
            assert store.readings[0]["reading"] == 100.0
            assert store.readings[1]["reading"] == 105.0
            assert store.readings[2]["reading"] == 110.0

    @pytest.mark.asyncio
    async def test_async_add_reading_raises_when_not_loaded(self, mock_hass: MagicMock) -> None:
        """Test that adding a reading raises when store is not loaded."""
        store = MeterStore(mock_hass, "test_entry")

        with pytest.raises(RuntimeError, match="Store not loaded"):
            await store.async_add_reading(
                reading=100.0,
                meter_number="GAS-12345",
                timestamp="2026-01-01T10:00:00+00:00",
            )

    def test_get_last_reading_returns_none_when_empty(self, mock_hass: MagicMock) -> None:
        """Test that get_last_reading returns None when no readings exist."""
        store = MeterStore(mock_hass, "test_entry")
        assert store.get_last_reading() is None

    def test_get_last_reading_returns_most_recent(self, mock_hass: MagicMock) -> None:
        """Test that get_last_reading returns the most recent reading."""
        store = MeterStore(mock_hass, "test_entry")
        store._data = {
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "currency": "EUR",
            "readings": [
                {
                    "meter_number": "GAS-12345",
                    "reading": 100.0,
                    "timestamp": "2026-01-01T10:00:00+00:00",
                    "image_path": None,
                },
                {
                    "meter_number": "GAS-12345",
                    "reading": 110.0,
                    "timestamp": "2026-01-15T10:00:00+00:00",
                    "image_path": None,
                },
            ],
            "prices": [],
        }

        last = store.get_last_reading()
        assert last is not None
        assert last["reading"] == 110.0

    def test_get_previous_reading_returns_none_when_less_than_two(self, mock_hass: MagicMock) -> None:
        """Test that get_previous_reading returns None with less than 2 readings."""
        store = MeterStore(mock_hass, "test_entry")
        store._data = {
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "currency": "EUR",
            "readings": [
                {
                    "meter_number": "GAS-12345",
                    "reading": 100.0,
                    "timestamp": "2026-01-01T10:00:00+00:00",
                    "image_path": None,
                }
            ],
            "prices": [],
        }

        assert store.get_previous_reading() is None

    def test_get_previous_reading_returns_second_to_last(self, mock_hass: MagicMock) -> None:
        """Test that get_previous_reading returns the second-to-last reading."""
        store = MeterStore(mock_hass, "test_entry")
        store._data = {
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "currency": "EUR",
            "readings": [
                {
                    "meter_number": "GAS-12345",
                    "reading": 100.0,
                    "timestamp": "2026-01-01T10:00:00+00:00",
                    "image_path": None,
                },
                {
                    "meter_number": "GAS-12345",
                    "reading": 110.0,
                    "timestamp": "2026-01-15T10:00:00+00:00",
                    "image_path": None,
                },
            ],
            "prices": [],
        }

        prev = store.get_previous_reading()
        assert prev is not None
        assert prev["reading"] == 100.0

    def test_get_first_reading_returns_none_when_empty(self, mock_hass: MagicMock) -> None:
        """Test that get_first_reading returns None when no readings exist."""
        store = MeterStore(mock_hass, "test_entry")
        assert store.get_first_reading() is None

    def test_get_first_reading_returns_first(self, mock_hass: MagicMock) -> None:
        """Test that get_first_reading returns the first reading."""
        store = MeterStore(mock_hass, "test_entry")
        store._data = {
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "currency": "EUR",
            "readings": [
                {
                    "meter_number": "GAS-12345",
                    "reading": 100.0,
                    "timestamp": "2026-01-01T10:00:00+00:00",
                    "image_path": None,
                },
                {
                    "meter_number": "GAS-12345",
                    "reading": 110.0,
                    "timestamp": "2026-01-15T10:00:00+00:00",
                    "image_path": None,
                },
            ],
            "prices": [],
        }

        first = store.get_first_reading()
        assert first is not None
        assert first["reading"] == 100.0


class TestMeterStorePrices:
    """Tests for price operations."""

    @pytest.mark.asyncio
    async def test_async_add_price(self, mock_hass: MagicMock) -> None:
        """Test adding a price."""
        with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
            mock_store_instance = MagicMock()
            mock_store_instance.async_load = AsyncMock(return_value=None)
            mock_store_instance.async_save = AsyncMock()
            mock_store_class.return_value = mock_store_instance

            store = MeterStore(mock_hass, "test_entry")
            await store.async_load(
                meter_type="gas",
                meter_name="Kitchen",
                meter_number="GAS-12345",
                currency="EUR",
            )

            await store.async_add_price(
                price_per_unit=1.50,
                valid_from="2026-01-01",
                currency="EUR",
            )

            assert len(store.prices) == 1
            assert store.prices[0]["price_per_unit"] == 1.50

    @pytest.mark.asyncio
    async def test_prices_sorted_by_valid_from(self, mock_hass: MagicMock) -> None:
        """Test that prices are sorted by valid_from date."""
        with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
            mock_store_instance = MagicMock()
            mock_store_instance.async_load = AsyncMock(return_value=None)
            mock_store_instance.async_save = AsyncMock()
            mock_store_class.return_value = mock_store_instance

            store = MeterStore(mock_hass, "test_entry")
            await store.async_load(
                meter_type="gas",
                meter_name="Kitchen",
                meter_number="GAS-12345",
                currency="EUR",
            )

            # Add prices out of order
            await store.async_add_price(
                price_per_unit=2.0,
                valid_from="2026-02-01",
                currency="EUR",
            )
            await store.async_add_price(
                price_per_unit=1.5,
                valid_from="2026-01-01",
                currency="EUR",
            )
            await store.async_add_price(
                price_per_unit=1.75,
                valid_from="2026-01-15",
                currency="EUR",
            )

            assert len(store.prices) == 3
            assert store.prices[0]["price_per_unit"] == 1.5
            assert store.prices[1]["price_per_unit"] == 1.75
            assert store.prices[2]["price_per_unit"] == 2.0

    @pytest.mark.asyncio
    async def test_async_add_price_raises_when_not_loaded(self, mock_hass: MagicMock) -> None:
        """Test that adding a price raises when store is not loaded."""
        store = MeterStore(mock_hass, "test_entry")

        with pytest.raises(RuntimeError, match="Store not loaded"):
            await store.async_add_price(
                price_per_unit=1.50,
                valid_from="2026-01-01",
                currency="EUR",
            )

    def test_get_current_price_returns_none_when_empty(self, mock_hass: MagicMock) -> None:
        """Test that get_current_price returns None when no prices exist."""
        store = MeterStore(mock_hass, "test_entry")
        assert store.get_current_price() is None

    def test_get_current_price_returns_none_when_all_future(self, mock_hass: MagicMock) -> None:
        """Test that get_current_price returns None when all prices are in the future."""
        store = MeterStore(mock_hass, "test_entry")
        store._data = {
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "currency": "EUR",
            "readings": [],
            "prices": [
                {
                    "price_per_unit": 2.0,
                    "valid_from": "2099-01-01",
                    "currency": "EUR",
                }
            ],
        }

        assert store.get_current_price() is None

    def test_get_current_price_returns_most_recent_valid(self, mock_hass: MagicMock) -> None:
        """Test that get_current_price returns the most recent price valid as of today."""
        store = MeterStore(mock_hass, "test_entry")
        store._data = {
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "currency": "EUR",
            "readings": [],
            "prices": [
                {
                    "price_per_unit": 1.5,
                    "valid_from": "2026-01-01",
                    "currency": "EUR",
                },
                {
                    "price_per_unit": 1.75,
                    "valid_from": "2026-02-01",
                    "currency": "EUR",
                },
            ],
        }

        current = store.get_current_price()
        # The exact price depends on the current date, but it should be one of the valid prices
        assert current is not None
        assert current["price_per_unit"] in [1.5, 1.75]

    def test_get_price_at_returns_none_when_empty(self, mock_hass: MagicMock) -> None:
        """Test that get_price_at returns None when no prices exist."""
        store = MeterStore(mock_hass, "test_entry")
        assert store.get_price_at("2026-01-01") is None

    def test_get_price_at_returns_price_valid_at_date(self, mock_hass: MagicMock) -> None:
        """Test that get_price_at returns the price valid at a given date."""
        store = MeterStore(mock_hass, "test_entry")
        store._data = {
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "currency": "EUR",
            "readings": [],
            "prices": [
                {
                    "price_per_unit": 1.5,
                    "valid_from": "2026-01-01",
                    "currency": "EUR",
                },
                {
                    "price_per_unit": 1.75,
                    "valid_from": "2026-02-01",
                    "currency": "EUR",
                },
            ],
        }

        # Date before second price
        price = store.get_price_at("2026-01-15")
        assert price is not None
        assert price["price_per_unit"] == 1.5

        # Date after second price
        price = store.get_price_at("2026-02-15")
        assert price is not None
        assert price["price_per_unit"] == 1.75

    def test_get_price_at_handles_iso_timestamps(self, mock_hass: MagicMock) -> None:
        """Test that get_price_at extracts date from ISO timestamp."""
        store = MeterStore(mock_hass, "test_entry")
        store._data = {
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "currency": "EUR",
            "readings": [],
            "prices": [
                {
                    "price_per_unit": 1.5,
                    "valid_from": "2026-01-01",
                    "currency": "EUR",
                }
            ],
        }

        price = store.get_price_at("2026-01-15T10:30:00+00:00")
        assert price is not None
        assert price["price_per_unit"] == 1.5


class TestMeterStoreImages:
    """Tests for image storage."""

    @pytest.mark.asyncio
    async def test_async_save_image(self, mock_hass: MagicMock) -> None:
        """Test saving an image."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_path = tmp_file.name

        try:
            with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
                mock_store_instance = MagicMock()
                mock_store_instance.async_load = MagicMock(return_value=None)
                mock_store_instance.async_save = MagicMock()
                mock_store_class.return_value = mock_store_instance

                store = MeterStore(mock_hass, "test_entry")
                dest_path = await store.async_save_image(
                    source_path=tmp_path,
                    entry_id="test_entry",
                    timestamp="2026-01-01T10:30:00+00:00",
                )

                assert dest_path is not None
                # The destination path should contain the timestamp and .jpg extension
                assert "2026_01_01_10" in dest_path or "20260101_10" in dest_path
                assert dest_path.endswith(".jpg")
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_async_save_image_preserves_extension(self, mock_hass: MagicMock) -> None:
        """Test that async_save_image preserves the image extension."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file.write(b"fake png data")
            tmp_path = tmp_file.name

        try:
            with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
                mock_store_instance = MagicMock()
                mock_store_instance.async_load = MagicMock(return_value=None)
                mock_store_instance.async_save = MagicMock()
                mock_store_class.return_value = mock_store_instance

                store = MeterStore(mock_hass, "test_entry")
                dest_path = await store.async_save_image(
                    source_path=tmp_path,
                    entry_id="test_entry",
                    timestamp="2026-01-01T10:30:00+00:00",
                )

                assert dest_path.endswith(".png")
        finally:
            os.unlink(tmp_path)


class TestMeterStoreRemoval:
    """Tests for removing store data."""

    @pytest.mark.asyncio
    async def test_async_remove(self, mock_hass: MagicMock) -> None:
        """Test removing stored data."""
        with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
            mock_store_instance = MagicMock()
            mock_store_instance.async_load = AsyncMock(return_value=None)
            mock_store_instance.async_save = AsyncMock()
            mock_store_instance.async_remove = AsyncMock()
            mock_store_class.return_value = mock_store_instance

            store = MeterStore(mock_hass, "test_entry")
            await store.async_load(
                meter_type="gas",
                meter_name="Kitchen",
                meter_number="GAS-12345",
                currency="EUR",
            )

            assert store.data is not None

            await store.async_remove()

            assert store.data is None
            mock_store_instance.async_remove.assert_called_once()

"""Tests for the Gas & Water Meter SQLite database layer."""

from __future__ import annotations

import contextlib
import os
import tempfile
from unittest.mock import patch

from custom_components.gas_water_meter.db import MeterDatabase
from homeassistant.core import HomeAssistant

from .conftest import MOCK_LEGACY_STORE_DATA


async def test_add_and_get_readings(mock_db: MeterDatabase) -> None:
    """Test adding and retrieving readings."""
    readings = await mock_db.async_get_readings("test_entry")
    assert len(readings) == 3
    assert readings[0]["reading"] == 100.0
    assert readings[1]["reading"] == 110.5
    assert readings[2]["reading"] == 125.3


async def test_readings_ordered_by_timestamp(mock_db: MeterDatabase) -> None:
    """Test that readings come back ordered by timestamp."""
    # Add reading with earlier timestamp
    await mock_db.async_add_reading(
        entry_id="test_entry",
        meter_number="GAS-12345",
        reading=95.0,
        timestamp="2025-12-15T10:00:00+00:00",
    )
    readings = await mock_db.async_get_readings("test_entry")
    assert len(readings) == 4
    # The new reading should be first (earliest)
    assert readings[0]["reading"] == 95.0


async def test_get_last_reading(mock_db: MeterDatabase) -> None:
    """Test getting the most recent reading."""
    last = await mock_db.async_get_last_reading("test_entry")
    assert last is not None
    assert last["reading"] == 125.3


async def test_get_previous_reading(mock_db: MeterDatabase) -> None:
    """Test getting the second-to-last reading."""
    prev = await mock_db.async_get_previous_reading("test_entry")
    assert prev is not None
    assert prev["reading"] == 110.5


async def test_get_first_reading(mock_db: MeterDatabase) -> None:
    """Test getting the oldest reading."""
    first = await mock_db.async_get_first_reading("test_entry")
    assert first is not None
    assert first["reading"] == 100.0


async def test_update_reading(mock_db: MeterDatabase) -> None:
    """Test updating an existing reading."""
    readings = await mock_db.async_get_readings("test_entry")
    reading_id = readings[0]["id"]

    ok = await mock_db.async_update_reading(reading_id, reading=99.5)
    assert ok is True

    updated = await mock_db.async_get_first_reading("test_entry")
    assert updated is not None
    assert updated["reading"] == 99.5


async def test_delete_reading(mock_db: MeterDatabase) -> None:
    """Test deleting a reading."""
    readings = await mock_db.async_get_readings("test_entry")
    reading_id = readings[0]["id"]

    ok = await mock_db.async_delete_reading(reading_id)
    assert ok is True

    remaining = await mock_db.async_get_readings("test_entry")
    assert len(remaining) == 2


async def test_delete_nonexistent_reading(mock_db: MeterDatabase) -> None:
    """Test deleting a reading that doesn't exist."""
    ok = await mock_db.async_delete_reading(99999)
    assert ok is False


async def test_reading_count(mock_db: MeterDatabase) -> None:
    """Test the reading count method."""
    count = await mock_db.async_get_reading_count("test_entry")
    assert count == 3

    count_empty = await mock_db.async_get_reading_count("nonexistent_entry")
    assert count_empty == 0


async def test_reading_pagination(mock_db: MeterDatabase) -> None:
    """Test paginated reading retrieval."""
    page1 = await mock_db.async_get_readings("test_entry", limit=2, offset=0)
    assert len(page1) == 2

    page2 = await mock_db.async_get_readings("test_entry", limit=2, offset=2)
    assert len(page2) == 1


# --- Prices ---


async def test_add_and_get_prices(mock_db: MeterDatabase) -> None:
    """Test adding and retrieving prices."""
    prices = await mock_db.async_get_prices("test_entry")
    assert len(prices) == 2
    assert prices[0]["price_per_unit"] == 1.50
    assert prices[1]["price_per_unit"] == 1.85


async def test_get_current_price(mock_db: MeterDatabase) -> None:
    """Test getting the currently active price."""
    current = await mock_db.async_get_current_price("test_entry")
    assert current is not None
    assert current["price_per_unit"] == 1.85


async def test_get_price_at_historical_date(mock_db: MeterDatabase) -> None:
    """Test getting the price valid at a historical date."""
    price = await mock_db.async_get_price_at("test_entry", "2025-06-15")
    assert price is not None
    assert price["price_per_unit"] == 1.50


async def test_get_price_at_recent_date(mock_db: MeterDatabase) -> None:
    """Test getting the price at a date in the current period."""
    price = await mock_db.async_get_price_at("test_entry", "2026-02-01T10:00:00+00:00")
    assert price is not None
    assert price["price_per_unit"] == 1.85


async def test_auto_close_previous_price(mock_db_empty: MeterDatabase) -> None:
    """Test that adding a new open-ended price closes the previous one."""
    db = mock_db_empty

    # Add first price (open-ended)
    await db.async_add_price(
        entry_id="test",
        price_per_unit=1.50,
        valid_from="2025-01-01",
        currency="EUR",
    )
    # Add second price (open-ended) - should close the first
    await db.async_add_price(
        entry_id="test",
        price_per_unit=1.85,
        valid_from="2026-01-01",
        currency="EUR",
    )

    prices = await db.async_get_prices("test")
    assert len(prices) == 2
    # First price should now have valid_to set
    assert prices[0]["valid_to"] == "2026-01-01"
    # Second price remains open
    assert prices[1]["valid_to"] is None


async def test_update_price(mock_db: MeterDatabase) -> None:
    """Test updating an existing price."""
    prices = await mock_db.async_get_prices("test_entry")
    price_id = prices[1]["id"]

    ok = await mock_db.async_update_price(price_id, price_per_unit=2.00)
    assert ok is True

    updated_prices = await mock_db.async_get_prices("test_entry")
    assert updated_prices[1]["price_per_unit"] == 2.00


async def test_delete_price(mock_db: MeterDatabase) -> None:
    """Test deleting a price."""
    prices = await mock_db.async_get_prices("test_entry")
    ok = await mock_db.async_delete_price(prices[0]["id"])
    assert ok is True

    remaining = await mock_db.async_get_prices("test_entry")
    assert len(remaining) == 1


# --- Empty DB ---


async def test_empty_db_returns_none(mock_db_empty: MeterDatabase) -> None:
    """Test that empty database returns None for query methods."""
    assert await mock_db_empty.async_get_last_reading("test_entry") is None
    assert await mock_db_empty.async_get_previous_reading("test_entry") is None
    assert await mock_db_empty.async_get_first_reading("test_entry") is None
    assert await mock_db_empty.async_get_current_price("test_entry") is None


# --- Statistics ---


async def test_consumption_stats(mock_db: MeterDatabase) -> None:
    """Test computing consumption statistics."""
    stats = await mock_db.async_get_consumption_stats("test_entry")
    assert len(stats) == 3
    # First entry has no consumption
    assert stats[0]["consumption"] is None
    # Second entry: 110.5 - 100.0 = 10.5
    assert stats[1]["consumption"] == 10.5
    # Third entry: 125.3 - 110.5 = 14.8
    assert abs(stats[2]["consumption"] - 14.8) < 0.001


# --- Cleanup ---


async def test_remove_entry(mock_db: MeterDatabase) -> None:
    """Test removing all data for an entry."""
    await mock_db.async_remove_entry("test_entry")
    assert await mock_db.async_get_reading_count("test_entry") == 0
    assert await mock_db.async_get_prices("test_entry") == []


# --- Migration ---


async def test_migrate_from_legacy_store(hass: HomeAssistant) -> None:
    """Test migrating data from the legacy JSON store to SQLite."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    with patch.object(hass.config, "path", return_value=tmp_path):
        db = MeterDatabase(hass)
        await db.async_setup()

    # Mock the legacy store to return data
    with patch(
        "custom_components.gas_water_meter.db.Store.async_load",
        return_value=MOCK_LEGACY_STORE_DATA,
    ):
        migrated = await db.async_migrate_from_store("test_legacy_entry")

    assert migrated is True

    # Verify data was migrated
    readings = await db.async_get_readings("test_legacy_entry")
    assert len(readings) == 3
    assert readings[0]["reading"] == 100.0

    prices = await db.async_get_prices("test_legacy_entry")
    assert len(prices) == 2
    # First price should have valid_to derived from second price's valid_from
    assert prices[0]["valid_to"] == "2026-01-01"
    # Last price remains open
    assert prices[1]["valid_to"] is None

    await db.async_close()
    os.unlink(tmp_path)


async def test_migrate_skips_if_already_migrated(mock_db: MeterDatabase) -> None:
    """Test that migration is skipped if data already exists in DB."""
    with patch(
        "custom_components.gas_water_meter.db.Store.async_load",
        return_value=MOCK_LEGACY_STORE_DATA,
    ):
        migrated = await mock_db.async_migrate_from_store("test_entry")

    # Should not migrate because test_entry already has data
    assert migrated is False


async def test_migrate_returns_false_for_no_legacy_data(
    mock_db_empty: MeterDatabase,
) -> None:
    """Test that migration returns False when there is no legacy data."""
    with patch(
        "custom_components.gas_water_meter.db.Store.async_load",
        return_value=None,
    ):
        migrated = await mock_db_empty.async_migrate_from_store("test_entry")

    assert migrated is False


# --- Image saving ---


async def test_save_image(hass: HomeAssistant) -> None:
    """Test that async_save_image copies the file to the media directory."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    with patch.object(hass.config, "path") as mock_path:
        mock_path.return_value = tmp_path
        db = MeterDatabase(hass)
        await db.async_setup()

    # Create a source image file
    src_fd, src_path = tempfile.mkstemp(suffix=".jpg")
    os.write(src_fd, b"fake image data")
    os.close(src_fd)

    # Create a temp directory for the media destination
    media_dir = tempfile.mkdtemp()
    with patch.object(hass.config, "path", return_value=media_dir):
        dest = await db.async_save_image(
            source_path=src_path,
            entry_id="test_entry",
            timestamp="2026-02-08T14:30:00+00:00",
        )

    def _verify() -> None:
        assert os.path.isfile(dest)
        with open(dest, "rb") as f:
            assert f.read() == b"fake image data"

    await hass.async_add_executor_job(_verify)

    # Close the DB before deleting the temp file (Windows locks .db files)
    await db.async_close()

    def _cleanup() -> None:
        for p in (src_path, dest, tmp_path):
            with contextlib.suppress(OSError):
                os.unlink(p)

    await hass.async_add_executor_job(_cleanup)


# --- Update edge cases ---


async def test_update_reading_no_fields(mock_db: MeterDatabase) -> None:
    """Test that updating a reading with no fields returns False."""
    readings = await mock_db.async_get_readings("test_entry")
    reading_id = readings[0]["id"]

    ok = await mock_db.async_update_reading(reading_id)
    assert ok is False


async def test_update_price_no_fields(mock_db: MeterDatabase) -> None:
    """Test that updating a price with no fields returns False."""
    prices = await mock_db.async_get_prices("test_entry")
    price_id = prices[0]["id"]

    ok = await mock_db.async_update_price(price_id)
    assert ok is False


async def test_get_price_at_no_applicable(mock_db: MeterDatabase) -> None:
    """Test get_price_at returns None for a date before all prices."""
    price = await mock_db.async_get_price_at("test_entry", "2020-01-01")
    assert price is None


# --- Meter number change ---


async def test_get_first_reading_for_meter(mock_db_empty: MeterDatabase) -> None:
    """Test async_get_first_reading_for_meter returns the oldest reading for a specific meter."""
    db = mock_db_empty

    await db.async_add_reading("e1", "OLD-001", 100.0, "2026-01-01T10:00:00+00:00")
    await db.async_add_reading("e1", "OLD-001", 150.0, "2026-03-01T10:00:00+00:00")
    await db.async_add_reading("e1", "NEW-002", 10.0, "2026-04-01T10:00:00+00:00")
    await db.async_add_reading("e1", "NEW-002", 30.0, "2026-05-01T10:00:00+00:00")

    first_new = await db.async_get_first_reading_for_meter("e1", "NEW-002")
    assert first_new is not None
    assert first_new["meter_number"] == "NEW-002"
    assert first_new["reading"] == 10.0

    first_old = await db.async_get_first_reading_for_meter("e1", "OLD-001")
    assert first_old is not None
    assert first_old["meter_number"] == "OLD-001"
    assert first_old["reading"] == 100.0


async def test_get_first_reading_for_meter_none(mock_db_empty: MeterDatabase) -> None:
    """Test async_get_first_reading_for_meter returns None for unknown meter number."""
    db = mock_db_empty
    await db.async_add_reading("e1", "GAS-001", 100.0, "2026-01-01T10:00:00+00:00")

    result = await db.async_get_first_reading_for_meter("e1", "UNKNOWN")
    assert result is None


async def test_schema_migration_v2_to_v3_adds_base_fee(hass: HomeAssistant) -> None:
    """Test that schema migration v2→v3 adds the base_fee column."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    # Create a DB at schema v2 (without base_fee column)
    import aiosqlite

    async with aiosqlite.connect(tmp_path) as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            )"""
        )
        await conn.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('schema_version', '2')"
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                price_per_unit REAL NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                currency TEXT NOT NULL,
                calorific_value REAL,
                condition_factor REAL,
                created_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                meter_number TEXT NOT NULL,
                reading REAL NOT NULL,
                timestamp TEXT NOT NULL,
                image_path TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        await conn.commit()

    # Open with MeterDatabase — migration should add base_fee
    with patch.object(hass.config, "path", return_value=tmp_path):
        db = MeterDatabase(hass)
        await db.async_setup()

    # Verify column exists by inserting a price with base_fee
    pid = await db.async_add_price(
        entry_id="test",
        price_per_unit=1.50,
        valid_from="2026-01-01",
        currency="EUR",
        base_fee=120.0,
    )
    prices = await db.async_get_prices("test")
    assert len(prices) == 1
    assert prices[0]["base_fee"] == 120.0

    await db.async_close()
    os.unlink(tmp_path)


async def test_add_price_with_base_fee(mock_db_empty: MeterDatabase) -> None:
    """Test that async_add_price stores the base_fee value."""
    db = mock_db_empty
    pid = await db.async_add_price(
        entry_id="test",
        price_per_unit=1.85,
        valid_from="2026-01-01",
        currency="EUR",
        base_fee=96.0,
    )
    prices = await db.async_get_prices("test")
    assert len(prices) == 1
    assert prices[0]["base_fee"] == 96.0


async def test_add_price_without_base_fee(mock_db_empty: MeterDatabase) -> None:
    """Test that async_add_price stores NULL when base_fee is omitted."""
    db = mock_db_empty
    await db.async_add_price(
        entry_id="test",
        price_per_unit=1.85,
        valid_from="2026-01-01",
        currency="EUR",
    )
    prices = await db.async_get_prices("test")
    assert len(prices) == 1
    assert prices[0]["base_fee"] is None


async def test_update_price_with_base_fee(mock_db_empty: MeterDatabase) -> None:
    """Test that async_update_price can set and clear base_fee."""
    db = mock_db_empty
    pid = await db.async_add_price(
        entry_id="test",
        price_per_unit=1.85,
        valid_from="2026-01-01",
        currency="EUR",
    )

    # Set base_fee
    ok = await db.async_update_price(pid, base_fee=150.0)
    assert ok is True
    prices = await db.async_get_prices("test")
    assert prices[0]["base_fee"] == 150.0

    # Clear base_fee (set to None)
    ok = await db.async_update_price(pid, base_fee=None)
    assert ok is True
    prices = await db.async_get_prices("test")
    assert prices[0]["base_fee"] is None


async def test_consumption_stats_meter_change(mock_db_empty: MeterDatabase) -> None:
    """Test async_get_consumption_stats resets consumption on meter number change."""
    db = mock_db_empty

    await db.async_add_reading("e1", "OLD-001", 100.0, "2026-01-01T10:00:00+00:00")
    await db.async_add_reading("e1", "OLD-001", 120.0, "2026-02-01T10:00:00+00:00")
    # Meter change
    await db.async_add_reading("e1", "NEW-002", 5.0, "2026-03-01T10:00:00+00:00")
    await db.async_add_reading("e1", "NEW-002", 15.0, "2026-04-01T10:00:00+00:00")

    stats = await db.async_get_consumption_stats("e1")

    assert len(stats) == 4

    # First reading: no consumption
    assert stats[0]["consumption"] is None
    assert stats[0]["meter_number"] == "OLD-001"

    # Second: same meter, consumption = 20
    assert stats[1]["consumption"] == 20.0
    assert stats[1]["meter_number"] == "OLD-001"

    # Third: meter changed, consumption resets to None
    assert stats[2]["consumption"] is None
    assert stats[2]["meter_number"] == "NEW-002"

    # Fourth: same meter, consumption = 10
    assert stats[3]["consumption"] == 10.0
    assert stats[3]["meter_number"] == "NEW-002"

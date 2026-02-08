"""SQLite database for Gas & Water Meter integration."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import aiosqlite
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY_PREFIX, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

# Sentinel for optional keyword arguments that distinguish "not provided" from None
_SENTINEL = object()

DB_FILENAME = "gas_water_meter.db"
DB_SCHEMA_VERSION = 1

_CREATE_READINGS = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    meter_number TEXT NOT NULL,
    reading REAL NOT NULL,
    timestamp TEXT NOT NULL,
    image_path TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

_CREATE_READINGS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_readings_entry
ON readings(entry_id, timestamp)
"""

_CREATE_PRICES = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    price_per_unit REAL NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    currency TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

_CREATE_PRICES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_prices_entry
ON prices(entry_id, valid_from)
"""

_CREATE_META = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""


class MeterDatabase:
    """SQLite-based persistent storage for all meters."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the database."""
        self._hass = hass
        self._db_path = hass.config.path(DB_FILENAME)
        self._db: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Open connection and create schema."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._create_schema()
        await self._db.commit()

    async def async_close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def _create_schema(self) -> None:
        """Create tables if they do not exist."""
        assert self._db is not None
        await self._db.execute(_CREATE_READINGS)
        await self._db.execute(_CREATE_READINGS_INDEX)
        await self._db.execute(_CREATE_PRICES)
        await self._db.execute(_CREATE_PRICES_INDEX)
        await self._db.execute(_CREATE_META)
        # Store schema version
        await self._db.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
            ("schema_version", str(DB_SCHEMA_VERSION)),
        )

    # ------------------------------------------------------------------
    # Migration from legacy JSON Store
    # ------------------------------------------------------------------

    async def async_migrate_from_store(self, entry_id: str) -> bool:
        """Migrate data from the legacy JSON Store for one entry.

        Returns True if migration happened, False if no legacy data found.
        """
        store: Store[dict[str, Any]] = Store(
            self._hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}_{entry_id}",
        )
        stored = await store.async_load()
        if stored is None:
            return False

        readings = stored.get("readings", [])
        prices = stored.get("prices", [])

        if not readings and not prices:
            return False

        # Check if already migrated (entry has readings in DB)
        existing = await self.async_get_readings(entry_id, limit=1)
        if existing:
            _LOGGER.debug("Entry %s already has data in DB, skipping migration", entry_id)
            return False

        _LOGGER.info(
            "Migrating %d readings and %d prices for entry %s from JSON to SQLite",
            len(readings),
            len(prices),
            entry_id,
        )

        # Import readings
        for r in readings:
            await self.async_add_reading(
                entry_id=entry_id,
                meter_number=r.get("meter_number", ""),
                reading=r["reading"],
                timestamp=r["timestamp"],
                image_path=r.get("image_path"),
            )

        # Import prices, deriving valid_to from successor
        sorted_prices = sorted(prices, key=lambda p: p["valid_from"])
        for i, p in enumerate(sorted_prices):
            valid_to = None
            if i < len(sorted_prices) - 1:
                valid_to = sorted_prices[i + 1]["valid_from"]
            await self.async_add_price(
                entry_id=entry_id,
                price_per_unit=p["price_per_unit"],
                valid_from=p["valid_from"],
                valid_to=valid_to,
                currency=p.get("currency", "EUR"),
            )

        _LOGGER.info("Migration complete for entry %s", entry_id)
        return True

    # ------------------------------------------------------------------
    # Readings - CRUD
    # ------------------------------------------------------------------

    async def async_add_reading(
        self,
        entry_id: str,
        meter_number: str,
        reading: float,
        timestamp: str,
        image_path: str | None = None,
    ) -> int:
        """Insert a new reading. Returns the new row id."""
        assert self._db is not None
        cursor = await self._db.execute(
            """INSERT INTO readings (entry_id, meter_number, reading, timestamp, image_path)
               VALUES (?, ?, ?, ?, ?)""",
            (entry_id, meter_number, reading, timestamp, image_path),
        )
        await self._db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def async_update_reading(
        self,
        reading_id: int,
        *,
        meter_number: str | None = None,
        reading: float | None = None,
        timestamp: str | None = None,
        image_path: str | None = _SENTINEL,  # type: ignore[assignment]
    ) -> bool:
        """Update an existing reading. Only provided fields are changed."""
        assert self._db is not None
        updates: list[str] = []
        params: list[Any] = []
        if meter_number is not None:
            updates.append("meter_number = ?")
            params.append(meter_number)
        if reading is not None:
            updates.append("reading = ?")
            params.append(reading)
        if timestamp is not None:
            updates.append("timestamp = ?")
            params.append(timestamp)
        if image_path is not _SENTINEL:
            updates.append("image_path = ?")
            params.append(image_path)
        if not updates:
            return False
        params.append(reading_id)
        cursor = await self._db.execute(
            f"UPDATE readings SET {', '.join(updates)} WHERE id = ?",  # noqa: S608
            params,
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def async_delete_reading(self, reading_id: int) -> bool:
        """Delete a reading by id."""
        assert self._db is not None
        cursor = await self._db.execute("DELETE FROM readings WHERE id = ?", (reading_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def async_get_readings(
        self,
        entry_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get readings for an entry, ordered by timestamp ascending."""
        assert self._db is not None
        sql = "SELECT * FROM readings WHERE entry_id = ? ORDER BY timestamp ASC"
        params: list[Any] = [entry_id]
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        cursor = await self._db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def async_get_reading_count(self, entry_id: str) -> int:
        """Return total number of readings for an entry."""
        assert self._db is not None
        cursor = await self._db.execute("SELECT COUNT(*) FROM readings WHERE entry_id = ?", (entry_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Readings - Query helpers (used by coordinator)
    # ------------------------------------------------------------------

    async def async_get_last_reading(self, entry_id: str) -> dict[str, Any] | None:
        """Return the most recent reading for an entry."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM readings WHERE entry_id = ? ORDER BY timestamp DESC LIMIT 1",
            (entry_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def async_get_previous_reading(self, entry_id: str) -> dict[str, Any] | None:
        """Return the second-to-last reading for an entry."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM readings WHERE entry_id = ? ORDER BY timestamp DESC LIMIT 1 OFFSET 1",
            (entry_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def async_get_first_reading(self, entry_id: str) -> dict[str, Any] | None:
        """Return the oldest reading for an entry."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM readings WHERE entry_id = ? ORDER BY timestamp ASC LIMIT 1",
            (entry_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Prices - CRUD
    # ------------------------------------------------------------------

    async def async_add_price(
        self,
        entry_id: str,
        price_per_unit: float,
        valid_from: str,
        valid_to: str | None = None,
        currency: str = "EUR",
    ) -> int:
        """Insert a new price. Auto-closes the previous open price if needed.

        Returns the new row id.
        """
        assert self._db is not None

        # If the new price has no end date, close the previous open-ended price
        if valid_to is None:
            await self._db.execute(
                """UPDATE prices
                   SET valid_to = ?
                   WHERE entry_id = ? AND valid_to IS NULL AND valid_from < ?""",
                (valid_from, entry_id, valid_from),
            )

        cursor = await self._db.execute(
            """INSERT INTO prices (entry_id, price_per_unit, valid_from, valid_to, currency)
               VALUES (?, ?, ?, ?, ?)""",
            (entry_id, price_per_unit, valid_from, valid_to, currency),
        )
        await self._db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def async_update_price(
        self,
        price_id: int,
        *,
        price_per_unit: float | None = None,
        valid_from: str | None = None,
        valid_to: str | None = _SENTINEL,  # type: ignore[assignment]
        currency: str | None = None,
    ) -> bool:
        """Update an existing price entry."""
        assert self._db is not None
        updates: list[str] = []
        params: list[Any] = []
        if price_per_unit is not None:
            updates.append("price_per_unit = ?")
            params.append(price_per_unit)
        if valid_from is not None:
            updates.append("valid_from = ?")
            params.append(valid_from)
        if valid_to is not _SENTINEL:
            updates.append("valid_to = ?")
            params.append(valid_to)
        if currency is not None:
            updates.append("currency = ?")
            params.append(currency)
        if not updates:
            return False
        params.append(price_id)
        cursor = await self._db.execute(
            f"UPDATE prices SET {', '.join(updates)} WHERE id = ?",  # noqa: S608
            params,
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def async_delete_price(self, price_id: int) -> bool:
        """Delete a price by id."""
        assert self._db is not None
        cursor = await self._db.execute("DELETE FROM prices WHERE id = ?", (price_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def async_get_prices(self, entry_id: str) -> list[dict[str, Any]]:
        """Get all prices for an entry, ordered by valid_from ascending."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM prices WHERE entry_id = ? ORDER BY valid_from ASC",
            (entry_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Prices - Query helpers (used by coordinator)
    # ------------------------------------------------------------------

    async def async_get_current_price(self, entry_id: str) -> dict[str, Any] | None:
        """Return the currently active price (valid_from <= today, no valid_to or valid_to >= today)."""
        assert self._db is not None
        cursor = await self._db.execute(
            """SELECT * FROM prices
               WHERE entry_id = ? AND valid_from <= date('now')
                 AND (valid_to IS NULL OR valid_to >= date('now'))
               ORDER BY valid_from DESC LIMIT 1""",
            (entry_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def async_get_price_at(self, entry_id: str, date_str: str) -> dict[str, Any] | None:
        """Return the price valid at a given date (YYYY-MM-DD or ISO timestamp)."""
        assert self._db is not None
        date_only = date_str[:10]
        cursor = await self._db.execute(
            """SELECT * FROM prices
               WHERE entry_id = ? AND valid_from <= ?
                 AND (valid_to IS NULL OR valid_to >= ?)
               ORDER BY valid_from DESC LIMIT 1""",
            (entry_id, date_only, date_only),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Statistics (for charts)
    # ------------------------------------------------------------------

    async def async_get_consumption_stats(self, entry_id: str) -> list[dict[str, Any]]:
        """Compute per-period consumption from readings.

        Returns a list of dicts with timestamp, reading, consumption, days.
        """
        readings = await self.async_get_readings(entry_id)
        stats: list[dict[str, Any]] = []
        for i, r in enumerate(readings):
            entry: dict[str, Any] = {
                "timestamp": r["timestamp"],
                "reading": r["reading"],
                "consumption": None,
                "days": None,
            }
            if i > 0:
                prev = readings[i - 1]
                entry["consumption"] = round(r["reading"] - prev["reading"], 3)
                entry["days"] = _days_between_str(prev["timestamp"], r["timestamp"])
            stats.append(entry)
        return stats

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def async_remove_entry(self, entry_id: str) -> None:
        """Remove all data for a config entry."""
        assert self._db is not None
        await self._db.execute("DELETE FROM readings WHERE entry_id = ?", (entry_id,))
        await self._db.execute("DELETE FROM prices WHERE entry_id = ?", (entry_id,))
        await self._db.commit()

    # ------------------------------------------------------------------
    # Image handling
    # ------------------------------------------------------------------

    async def async_save_image(
        self,
        source_path: str,
        entry_id: str,
        timestamp: str,
    ) -> str:
        """Copy a meter image to persistent storage and return the destination path."""
        media_dir = self._hass.config.path("media", "gas_water_meter", entry_id)

        def _copy_image() -> str:
            os.makedirs(media_dir, exist_ok=True)
            safe_ts = timestamp.replace(":", "").replace("-", "").replace("T", "_").replace("+", "_")
            ext = Path(source_path).suffix or ".jpg"
            dest_filename = f"{safe_ts}{ext}"
            dest_path = os.path.join(media_dir, dest_filename)
            shutil.copy2(source_path, dest_path)
            return dest_path

        return await self._hass.async_add_executor_job(_copy_image)


def _days_between_str(ts1: str, ts2: str) -> float | None:
    """Calculate the number of days between two ISO timestamp strings."""
    from datetime import datetime  # noqa: PLC0415

    try:
        dt1 = datetime.fromisoformat(ts1)
        dt2 = datetime.fromisoformat(ts2)
        return round((dt2 - dt1).total_seconds() / 86400.0, 1)
    except (ValueError, TypeError):
        return None

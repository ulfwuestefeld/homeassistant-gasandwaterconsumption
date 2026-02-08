"""Persistent storage for Gas & Water Meter integration."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY_PREFIX, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class ReadingEntry(TypedDict):
    """A single meter reading entry."""

    meter_number: str
    reading: float
    timestamp: str
    image_path: str | None


class PriceEntry(TypedDict):
    """A single price entry."""

    price_per_unit: float
    valid_from: str
    currency: str


class MeterData(TypedDict):
    """Full stored data for a meter."""

    meter_type: str
    meter_name: str
    meter_number: str
    currency: str
    readings: list[ReadingEntry]
    prices: list[PriceEntry]


class MeterStore:
    """Handle persistent storage for a single meter."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the meter store."""
        self._hass = hass
        self._entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}_{entry_id}",
        )
        self._data: MeterData | None = None

    @property
    def data(self) -> MeterData | None:
        """Return the current stored data."""
        return self._data

    @property
    def readings(self) -> list[ReadingEntry]:
        """Return the list of readings."""
        if self._data is None:
            return []
        return self._data["readings"]

    @property
    def prices(self) -> list[PriceEntry]:
        """Return the list of prices."""
        if self._data is None:
            return []
        return self._data["prices"]

    async def async_load(
        self,
        meter_type: str,
        meter_name: str,
        meter_number: str,
        currency: str,
    ) -> MeterData:
        """Load data from storage, creating defaults if needed."""
        stored = await self._store.async_load()
        if stored is not None:
            self._data = MeterData(
                meter_type=stored.get("meter_type", meter_type),
                meter_name=stored.get("meter_name", meter_name),
                meter_number=stored.get("meter_number", meter_number),
                currency=stored.get("currency", currency),
                readings=stored.get("readings", []),
                prices=stored.get("prices", []),
            )
        else:
            self._data = MeterData(
                meter_type=meter_type,
                meter_name=meter_name,
                meter_number=meter_number,
                currency=currency,
                readings=[],
                prices=[],
            )
            await self._async_save()
        return self._data

    async def async_add_reading(
        self,
        reading: float,
        meter_number: str,
        timestamp: str,
        image_path: str | None = None,
    ) -> None:
        """Add a new meter reading and persist."""
        if self._data is None:
            msg = "Store not loaded"
            raise RuntimeError(msg)

        entry = ReadingEntry(
            meter_number=meter_number,
            reading=reading,
            timestamp=timestamp,
            image_path=image_path,
        )
        self._data["readings"].append(entry)
        # Keep sorted by timestamp
        self._data["readings"].sort(key=lambda r: r["timestamp"])
        await self._async_save()

    async def async_add_price(
        self,
        price_per_unit: float,
        valid_from: str,
        currency: str,
    ) -> None:
        """Add a new price entry and persist."""
        if self._data is None:
            msg = "Store not loaded"
            raise RuntimeError(msg)

        entry = PriceEntry(
            price_per_unit=price_per_unit,
            valid_from=valid_from,
            currency=currency,
        )
        self._data["prices"].append(entry)
        # Keep sorted by valid_from
        self._data["prices"].sort(key=lambda p: p["valid_from"])
        await self._async_save()

    def get_last_reading(self) -> ReadingEntry | None:
        """Return the most recent reading."""
        if not self.readings:
            return None
        return self.readings[-1]

    def get_previous_reading(self) -> ReadingEntry | None:
        """Return the second-to-last reading."""
        if len(self.readings) < 2:  # noqa: PLR2004
            return None
        return self.readings[-2]

    def get_first_reading(self) -> ReadingEntry | None:
        """Return the first reading."""
        if not self.readings:
            return None
        return self.readings[0]

    def get_current_price(self) -> PriceEntry | None:
        """Return the currently active price (most recent valid_from <= now)."""
        if not self.prices:
            return None
        now = datetime.now().strftime("%Y-%m-%d")
        applicable = [p for p in self.prices if p["valid_from"] <= now]
        if not applicable:
            return None
        return applicable[-1]

    def get_price_at(self, date_str: str) -> PriceEntry | None:
        """Return the price valid at a given date string (YYYY-MM-DD or ISO)."""
        if not self.prices:
            return None
        # Extract date portion if full ISO timestamp
        date_only = date_str[:10]
        applicable = [p for p in self.prices if p["valid_from"] <= date_only]
        if not applicable:
            return None
        return applicable[-1]

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
            # Create a safe filename from the timestamp
            safe_ts = timestamp.replace(":", "").replace("-", "").replace("T", "_").replace("+", "_")
            ext = os.path.splitext(source_path)[1] or ".jpg"
            dest_filename = f"{safe_ts}{ext}"
            dest_path = os.path.join(media_dir, dest_filename)
            shutil.copy2(source_path, dest_path)
            return dest_path

        return await self._hass.async_add_executor_job(_copy_image)

    async def async_remove(self) -> None:
        """Remove stored data."""
        await self._store.async_remove()
        self._data = None

    async def _async_save(self) -> None:
        """Save data to storage."""
        if self._data is not None:
            await self._store.async_save(dict(self._data))

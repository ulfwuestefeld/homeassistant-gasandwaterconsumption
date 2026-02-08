"""Data coordinator for Gas & Water Meter integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_CURRENCY,
    CONF_METER_NAME,
    CONF_METER_NUMBER,
    CONF_METER_TYPE,
    DAYS_PER_MONTH,
    DAYS_PER_YEAR,
    DOMAIN,
)
from .db import MeterDatabase

_LOGGER = logging.getLogger(__name__)


@dataclass
class MeterCoordinatorData:
    """Computed data from stored readings and prices."""

    # Core
    reading: float | None = None
    meter_number: str | None = None
    last_entry_date: str | None = None
    consumption: float | None = None
    days_between: float | None = None

    # Projection
    daily_average: float | None = None
    monthly_projection: float | None = None
    yearly_projection: float | None = None

    # Cost
    current_price: float | None = None
    last_period_cost: float | None = None
    monthly_projected_cost: float | None = None
    yearly_projected_cost: float | None = None

    # Metadata
    meter_type: str = ""
    meter_name: str = ""
    currency: str = "EUR"
    last_image_path: str | None = None

    # Extra attributes for sensors
    extra: dict[str, Any] = field(default_factory=dict)


_UPDATE_INTERVAL = timedelta(seconds=60)


class MeterCoordinator(DataUpdateCoordinator[MeterCoordinatorData]):
    """Coordinator for a single meter.

    Data is refreshed immediately when new readings or prices are recorded
    via services or WebSocket commands.  A 60-second polling interval acts
    as a safety net so sensors always converge on the latest DB state.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, db: MeterDatabase) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            config_entry=entry,
            update_interval=_UPDATE_INTERVAL,
        )
        self.db = db
        self._entry_id: str = entry.entry_id
        self._meter_type: str = entry.data[CONF_METER_TYPE]
        self._meter_name: str = entry.data[CONF_METER_NAME]
        self._meter_number: str = entry.data[CONF_METER_NUMBER]
        self._currency: str = entry.data.get(CONF_CURRENCY, "EUR")

    async def _async_update_data(self) -> MeterCoordinatorData:
        """Compute all sensor values from stored data."""
        data = await self._compute_data()
        _LOGGER.debug(
            "Coordinator %s refreshed: reading=%s, consumption=%s, price=%s",
            self._entry_id,
            data.reading,
            data.consumption,
            data.current_price,
        )
        return data

    async def _compute_data(self) -> MeterCoordinatorData:
        """Compute all derived values from DB readings and prices."""
        data = MeterCoordinatorData(
            meter_type=self._meter_type,
            meter_name=self._meter_name,
            currency=self._currency,
        )

        last = await self.db.async_get_last_reading(self._entry_id)
        prev = await self.db.async_get_previous_reading(self._entry_id)
        first = await self.db.async_get_first_reading(self._entry_id)

        if last is None:
            _LOGGER.debug("No readings found for entry %s", self._entry_id)
            return data

        # Core values
        data.reading = last["reading"]
        data.meter_number = last["meter_number"]
        data.last_entry_date = last["timestamp"]
        data.last_image_path = last.get("image_path")

        if prev is not None:
            data.consumption = round(last["reading"] - prev["reading"], 3)
            days = _days_between(prev["timestamp"], last["timestamp"])
            if days is not None and days > 0:
                data.days_between = round(days, 1)

        # Projection: requires at least 2 readings
        if first is not None and first["id"] != last["id"]:
            total_days = _days_between(first["timestamp"], last["timestamp"])
            if total_days is not None and total_days > 0:
                total_consumption = last["reading"] - first["reading"]
                data.daily_average = round(total_consumption / total_days, 4)
                data.monthly_projection = round(data.daily_average * DAYS_PER_MONTH, 3)
                data.yearly_projection = round(data.daily_average * DAYS_PER_YEAR, 3)

        # Cost calculations
        await self._compute_costs(data, prev)

        return data

    async def _compute_costs(
        self,
        data: MeterCoordinatorData,
        prev: dict[str, Any] | None,
    ) -> None:
        """Fill cost fields in data."""
        current_price_entry = await self.db.async_get_current_price(self._entry_id)
        if current_price_entry is None:
            return

        data.current_price = current_price_entry["price_per_unit"]

        # Last period cost
        if data.consumption is not None and prev is not None:
            period_price = await self.db.async_get_price_at(self._entry_id, prev["timestamp"])
            if period_price is not None:
                data.last_period_cost = round(data.consumption * period_price["price_per_unit"], 2)

        # Projected costs
        if data.monthly_projection is not None:
            data.monthly_projected_cost = round(data.monthly_projection * data.current_price, 2)
        if data.yearly_projection is not None:
            data.yearly_projected_cost = round(data.yearly_projection * data.current_price, 2)


def _days_between(ts1: str, ts2: str) -> float | None:
    """Calculate the number of days between two ISO timestamp strings."""
    try:
        dt1 = datetime.fromisoformat(ts1)
        dt2 = datetime.fromisoformat(ts2)
        delta = dt2 - dt1
        return delta.total_seconds() / 86400.0
    except (ValueError, TypeError):
        return None

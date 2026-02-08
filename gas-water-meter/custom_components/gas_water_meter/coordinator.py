"""Data coordinator for Gas & Water Meter integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
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
from .store import MeterStore

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


class MeterCoordinator(DataUpdateCoordinator[MeterCoordinatorData]):
    """Coordinator for a single meter.

    This coordinator does not poll. It is refreshed manually when new data
    is recorded via services.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            config_entry=entry,
            # No update_interval -- manual refresh only
        )
        self.store = MeterStore(hass, entry.entry_id)
        self._meter_type: str = entry.data[CONF_METER_TYPE]
        self._meter_name: str = entry.data[CONF_METER_NAME]
        self._meter_number: str = entry.data[CONF_METER_NUMBER]
        self._currency: str = entry.data.get(CONF_CURRENCY, "EUR")

    async def async_setup(self) -> None:
        """Load stored data on first setup."""
        await self.store.async_load(
            meter_type=self._meter_type,
            meter_name=self._meter_name,
            meter_number=self._meter_number,
            currency=self._currency,
        )

    async def _async_update_data(self) -> MeterCoordinatorData:
        """Compute all sensor values from stored data."""
        return self._compute_data()

    def _compute_data(self) -> MeterCoordinatorData:
        """Compute all derived values from stored readings and prices."""
        data = MeterCoordinatorData(
            meter_type=self._meter_type,
            meter_name=self._meter_name,
            currency=self._currency,
        )

        last = self.store.get_last_reading()
        prev = self.store.get_previous_reading()
        first = self.store.get_first_reading()

        if last is None:
            return data

        # Core values
        data.reading = last["reading"]
        data.meter_number = last["meter_number"]
        data.last_entry_date = last["timestamp"]
        data.last_image_path = last.get("image_path")

        if prev is not None:
            # Consumption delta
            data.consumption = round(last["reading"] - prev["reading"], 3)

            # Days between readings
            days = _days_between(prev["timestamp"], last["timestamp"])
            if days is not None and days > 0:
                data.days_between = round(days, 1)

        # Projection: requires at least 2 readings
        if first is not None and first is not last:
            total_days = _days_between(first["timestamp"], last["timestamp"])
            if total_days is not None and total_days > 0:
                total_consumption = last["reading"] - first["reading"]
                data.daily_average = round(total_consumption / total_days, 4)
                data.monthly_projection = round(data.daily_average * DAYS_PER_MONTH, 3)
                data.yearly_projection = round(data.daily_average * DAYS_PER_YEAR, 3)

        # Cost calculations
        current_price_entry = self.store.get_current_price()
        if current_price_entry is not None:
            data.current_price = current_price_entry["price_per_unit"]

            # Last period cost
            if data.consumption is not None and prev is not None:
                # Use price valid at the start of the period
                period_price = self.store.get_price_at(prev["timestamp"])
                if period_price is not None:
                    data.last_period_cost = round(data.consumption * period_price["price_per_unit"], 2)

            # Projected costs
            if data.monthly_projection is not None:
                data.monthly_projected_cost = round(data.monthly_projection * data.current_price, 2)
            if data.yearly_projection is not None:
                data.yearly_projected_cost = round(data.yearly_projection * data.current_price, 2)

        return data


def _days_between(ts1: str, ts2: str) -> float | None:
    """Calculate the number of days between two ISO timestamp strings."""
    try:
        dt1 = datetime.fromisoformat(ts1)
        dt2 = datetime.fromisoformat(ts2)
        delta = dt2 - dt1
        return delta.total_seconds() / 86400.0
    except (ValueError, TypeError):
        return None

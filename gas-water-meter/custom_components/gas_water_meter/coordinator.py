"""Data coordinator for Gas & Water Meter integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_CALORIFIC_VALUE,
    CONF_CONDITION_FACTOR,
    CONF_CURRENCY,
    CONF_METER_NAME,
    CONF_METER_NUMBER,
    CONF_METER_TYPE,
    DAYS_PER_MONTH,
    DAYS_PER_YEAR,
    DEFAULT_CALORIFIC_VALUE,
    DEFAULT_CONDITION_FACTOR,
    DOMAIN,
    METER_TYPE_GAS,
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

    # Gas energy conversion (only for gas meters)
    energy_consumption: float | None = None  # kWh for last period

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

    # Gas conversion factors (stored for sensor access)
    calorific_value: float | None = None
    condition_factor: float | None = None

    # Annual base fee from current price entry
    current_base_fee: float | None = None

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

        # Gas-specific default conversion factors (config-entry level).
        # These serve as fallback when a price entry has no explicit factors.
        self._default_calorific_value: float = entry.data.get(
            CONF_CALORIFIC_VALUE,
            DEFAULT_CALORIFIC_VALUE,
        )
        self._default_condition_factor: float = entry.data.get(
            CONF_CONDITION_FACTOR,
            DEFAULT_CONDITION_FACTOR,
        )

        # Change detection for statistics import
        self._last_stats_fingerprint: tuple[tuple[Any, ...], ...] | None = None

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

        # Sync reading statistics to HA long-term statistics so the Energy
        # Dashboard shows consumption at the actual reading dates.
        await self._sync_energy_statistics()

        return data

    # ------------------------------------------------------------------
    # Gas conversion helpers
    # ------------------------------------------------------------------

    def _resolve_gas_factors(
        self,
        price_entry: dict[str, Any] | None = None,
    ) -> tuple[float, float]:
        """Return (calorific_value, condition_factor) for a price entry.

        Per-price factors take precedence; the config-entry defaults are
        used when the price row has NULL values (e.g. legacy data before
        the schema-v2 migration).
        """
        cv = price_entry.get("calorific_value") if price_entry is not None else None
        cf = price_entry.get("condition_factor") if price_entry is not None else None
        return (
            cv if cv is not None else self._default_calorific_value,
            cf if cf is not None else self._default_condition_factor,
        )

    @staticmethod
    def _m3_to_kwh(m3: float, calorific_value: float, condition_factor: float) -> float:
        """Convert m³ gas consumption to kWh."""
        return m3 * calorific_value * condition_factor

    def _compute_cost(
        self,
        consumption_m3: float,
        price_per_unit: float,
        calorific_value: float,
        condition_factor: float,
    ) -> float:
        """Compute cost from m³ consumption and price.

        For gas: price is in ct/kWh, so cost = kWh * price / 100 (EUR).
        For water: price is in EUR/m³, so cost = m³ * price (EUR).
        """
        if self._meter_type == METER_TYPE_GAS:
            kwh = self._m3_to_kwh(consumption_m3, calorific_value, condition_factor)
            return round(kwh * price_per_unit / 100.0, 2)
        return round(consumption_m3 * price_per_unit, 2)

    async def _compute_data(self) -> MeterCoordinatorData:
        """Compute all derived values from DB readings and prices."""
        data = MeterCoordinatorData(
            meter_type=self._meter_type,
            meter_name=self._meter_name,
            currency=self._currency,
        )

        last = await self.db.async_get_last_reading(self._entry_id)
        prev = await self.db.async_get_previous_reading(self._entry_id)

        # Resolve gas conversion factors from current price (or defaults).
        current_price_entry = await self.db.async_get_current_price(self._entry_id)
        if self._meter_type == METER_TYPE_GAS:
            cv, cf = self._resolve_gas_factors(current_price_entry)
            data.calorific_value = cv
            data.condition_factor = cf

        # Annual base fee from current price entry (applies to all meter types)
        if current_price_entry is not None:
            data.current_base_fee = current_price_entry.get("base_fee")

        if last is None:
            _LOGGER.debug("No readings found for entry %s", self._entry_id)
            return data

        # Core values
        data.reading = last["reading"]
        data.meter_number = last["meter_number"]
        data.last_entry_date = last["timestamp"]
        data.last_image_path = last.get("image_path")

        # Consumption: only when the meter number matches the previous entry.
        # A meter number change (e.g. meter replacement) resets the delta.
        same_meter = prev is not None and prev["meter_number"] == last["meter_number"]
        if same_meter:
            data.consumption = round(last["reading"] - prev["reading"], 3)
            days = _days_between(prev["timestamp"], last["timestamp"])
            if days is not None and days > 0:
                data.days_between = round(days, 1)

            # Gas: compute energy consumption in kWh using the price factors
            # that were active at the start of the consumption period.
            if self._meter_type == METER_TYPE_GAS and data.consumption is not None:
                period_price = await self.db.async_get_price_at(self._entry_id, prev["timestamp"])
                ecv, ecf = self._resolve_gas_factors(period_price)
                data.energy_consumption = round(
                    self._m3_to_kwh(data.consumption, ecv, ecf),
                    3,
                )

        # Projection: based only on readings with the current meter number.
        first = await self.db.async_get_first_reading_for_meter(self._entry_id, last["meter_number"])
        if first is not None and first["id"] != last["id"]:
            total_days = _days_between(first["timestamp"], last["timestamp"])
            if total_days is not None and total_days > 0:
                total_consumption = last["reading"] - first["reading"]
                data.daily_average = round(total_consumption / total_days, 4)
                data.monthly_projection = round(data.daily_average * DAYS_PER_MONTH, 3)
                data.yearly_projection = round(data.daily_average * DAYS_PER_YEAR, 3)

        # Cost calculations (prev is only used when same meter)
        await self._compute_costs(data, prev if same_meter else None, current_price_entry)

        return data

    @staticmethod
    def _prorate_base_fee(base_fee: float | None, days: float) -> float:
        """Pro-rate an annual base fee to a given number of days.

        Returns 0.0 when *base_fee* is ``None`` (backwards-compatible).
        """
        if base_fee is None:
            return 0.0
        return round(base_fee * days / DAYS_PER_YEAR, 2)

    async def _compute_costs(
        self,
        data: MeterCoordinatorData,
        prev: dict[str, Any] | None,
        current_price_entry: dict[str, Any] | None,
    ) -> None:
        """Fill cost fields in data.

        Each price entry carries its own gas conversion factors.  The
        factors from the period-specific price are used for historical
        cost (last_period_cost) while the current price's factors are
        used for projected costs.

        An annual base fee (Jahresgrundgebühr) from the price entry is
        pro-rated and added to every cost figure.

        Gas: price is in ct/kWh, cost = m³ * Brennwert * Zustandszahl * price / 100.
        Water: price is in EUR/m³, cost = m³ * price.
        """
        if current_price_entry is None:
            return

        data.current_price = current_price_entry["price_per_unit"]
        cur_cv, cur_cf = self._resolve_gas_factors(current_price_entry)
        cur_base_fee = current_price_entry.get("base_fee")

        # Last period cost — uses the price (and factors) that were active
        # at the start of the consumption period.
        if data.consumption is not None and prev is not None:
            period_price = await self.db.async_get_price_at(self._entry_id, prev["timestamp"])
            if period_price is not None:
                pp_cv, pp_cf = self._resolve_gas_factors(period_price)
                consumption_cost = self._compute_cost(
                    data.consumption,
                    period_price["price_per_unit"],
                    pp_cv,
                    pp_cf,
                )
                pp_base_fee = period_price.get("base_fee")
                prorated = self._prorate_base_fee(pp_base_fee, data.days_between or 0.0)
                data.last_period_cost = round(consumption_cost + prorated, 2)

        # Projected costs — use current price and its factors.
        if data.monthly_projection is not None:
            consumption_cost = self._compute_cost(
                data.monthly_projection,
                data.current_price,
                cur_cv,
                cur_cf,
            )
            prorated = self._prorate_base_fee(cur_base_fee, DAYS_PER_MONTH)
            data.monthly_projected_cost = round(consumption_cost + prorated, 2)
        if data.yearly_projection is not None:
            consumption_cost = self._compute_cost(
                data.yearly_projection,
                data.current_price,
                cur_cv,
                cur_cf,
            )
            # Yearly: full base fee (no pro-rating needed)
            data.yearly_projected_cost = round(
                consumption_cost + (cur_base_fee or 0.0),
                2,
            )

    # ------------------------------------------------------------------
    # External statistics import for the Energy Dashboard
    # ------------------------------------------------------------------

    async def _sync_energy_statistics(self) -> None:
        """Sync reading statistics to HA long-term statistics.

        The Energy Dashboard normally records sensor state changes with
        the *current* timestamp (i.e. when the value was written to HA).
        For manually entered historical readings this is wrong -- the
        consumption should appear at the *reading* date, not the entry
        date.

        This method imports all readings as **external statistics**
        (source = DOMAIN) with the reading's actual timestamp.  The
        Energy Dashboard can then be configured to use the external
        statistic ``gas_water_meter:<entry_id>`` instead of the sensor
        entity, giving correct historical charts.
        """
        readings = await self.db.async_get_readings(self._entry_id)

        # Change detection: skip re-import when nothing changed.
        fingerprint = tuple((r["id"], r["reading"], r["timestamp"], r["meter_number"]) for r in readings)
        if fingerprint == self._last_stats_fingerprint:
            return
        self._last_stats_fingerprint = fingerprint

        if not readings:
            return

        try:
            # Clean up old statistics with uppercase entry_id (migration from v0.1.9)
            await self._async_cleanup_old_statistics()
            await self._do_import_statistics(readings)
        except Exception:
            _LOGGER.warning(
                "Failed to import reading statistics for %s",
                self._entry_id,
                exc_info=True,
            )

    async def _do_import_statistics(self, readings: list[dict[str, Any]]) -> None:
        """Build and import external statistics from DB readings.

        Each reading produces one ``StatisticData`` entry whose ``start``
        is the reading timestamp rounded down to the full hour (required
        by HA).  ``state`` is the raw meter reading; ``sum`` is the
        cumulative consumption since the first reading, correctly handling
        meter replacements (different meter numbers).

        If two readings fall into the same hour, the later one wins.
        """
        from homeassistant.components.recorder.models import (  # noqa: PLC0415
            StatisticData,
            StatisticMetaData,
        )
        from homeassistant.components.recorder.statistics import (  # noqa: PLC0415
            async_import_statistics,
        )

        sorted_readings = sorted(readings, key=lambda r: r["timestamp"])

        running_sum = 0.0
        hourly: dict[datetime, StatisticData] = {}

        for i, reading in enumerate(sorted_readings):
            # Accumulate consumption (only between same meter numbers).
            if i > 0:
                prev = sorted_readings[i - 1]
                if reading["meter_number"] == prev["meter_number"]:
                    delta = reading["reading"] - prev["reading"]
                    if delta > 0:
                        running_sum += delta

            ts = datetime.fromisoformat(reading["timestamp"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)

            # Statistics require the start of the hour.
            start = ts.replace(minute=0, second=0, microsecond=0)

            # Later readings within the same hour overwrite earlier ones.
            hourly[start] = StatisticData(
                start=start,
                state=reading["reading"],
                sum=round(running_sum, 3),
            )

        stats = [hourly[k] for k in sorted(hourly)]

        name = self.config_entry.title or self._meter_name
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=name,
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:{self._entry_id.lower()}",
            unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        )

        await async_import_statistics(self.hass, metadata, stats)

        _LOGGER.debug(
            "Imported %d statistics for %s (statistic_id=%s:%s)",
            len(stats),
            name,
            DOMAIN,
            self._entry_id.lower(),
        )

    async def _async_cleanup_old_statistics(self) -> None:
        """Remove old statistics with uppercase entry_id.

        Migration from v0.1.9: entry_ids with uppercase letters were invalid.
        This cleanup removes the old erroneous statistics and allows reimport
        with the corrected lowercase statistic_id.
        """
        old_statistic_id = f"{DOMAIN}:{self._entry_id}"
        try:
            from homeassistant.components.recorder.statistics import (  # noqa: PLC0415
                delete_statistics,
            )

            delete_statistics(self.hass, [old_statistic_id])
            _LOGGER.debug("Cleaned up old statistics with id %s", old_statistic_id)
        except ImportError:
            # delete_statistics not available in this HA version, skip cleanup
            _LOGGER.debug(
                "delete_statistics not available, skipping cleanup for %s",
                old_statistic_id,
            )
        except Exception as err:
            # Silently ignore if the old statistics don't exist
            _LOGGER.debug(
                "No old statistics to clean up for %s: %s",
                old_statistic_id,
                err,
            )


def _days_between(ts1: str, ts2: str) -> float | None:
    """Calculate the number of days between two ISO timestamp strings."""
    try:
        dt1 = datetime.fromisoformat(ts1)
        dt2 = datetime.fromisoformat(ts2)
        delta = dt2 - dt1
        return delta.total_seconds() / 86400.0
    except (ValueError, TypeError):
        return None

"""Sensor platform for Gas & Water Meter integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GasWaterMeterConfigEntry
from .const import (
    CONF_METER_TYPE,
    DEVICE_NAME_PREFIX,
    DOMAIN,
    ICONS,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
)
from .coordinator import MeterCoordinator, MeterCoordinatorData


@dataclass(kw_only=True)
class MeterSensorDescription(SensorEntityDescription):
    """Sensor entity description for a meter sensor."""

    value_fn: Callable[[MeterCoordinatorData], StateType]
    gas_device_class: SensorDeviceClass | None = None
    water_device_class: SensorDeviceClass | None = None
    dynamic_unit: bool = False  # If True, use currency from coordinator data


def _gas_water_device_class(desc: MeterSensorDescription, meter_type: str) -> SensorDeviceClass | None:
    """Get the device class based on meter type."""
    if meter_type == METER_TYPE_GAS and desc.gas_device_class is not None:
        return desc.gas_device_class
    if meter_type == METER_TYPE_WATER and desc.water_device_class is not None:
        return desc.water_device_class
    return desc.device_class


# Sensor descriptions for all 12 sensors
SENSOR_DESCRIPTIONS: tuple[MeterSensorDescription, ...] = (
    # --- Core Sensors ---
    MeterSensorDescription(
        key="reading",
        translation_key="reading",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        gas_device_class=SensorDeviceClass.GAS,
        water_device_class=SensorDeviceClass.WATER,
        suggested_display_precision=3,
        value_fn=lambda data: data.reading,
    ),
    MeterSensorDescription(
        key="meter_number",
        translation_key="meter_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.meter_number,
    ),
    MeterSensorDescription(
        key="last_entry_date",
        translation_key="last_entry_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_entry_date,
    ),
    MeterSensorDescription(
        key="consumption",
        translation_key="consumption",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        gas_device_class=SensorDeviceClass.GAS,
        water_device_class=SensorDeviceClass.WATER,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        value_fn=lambda data: data.consumption,
    ),
    MeterSensorDescription(
        key="days_between",
        translation_key="days_between",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=lambda data: data.days_between,
    ),
    # --- Projection Sensors ---
    MeterSensorDescription(
        key="daily_average",
        translation_key="daily_average",
        state_class=SensorStateClass.MEASUREMENT,
        gas_device_class=SensorDeviceClass.GAS,
        water_device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=f"{UnitOfVolume.CUBIC_METERS}/d",
        suggested_display_precision=4,
        value_fn=lambda data: data.daily_average,
    ),
    MeterSensorDescription(
        key="monthly_projection",
        translation_key="monthly_projection",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        gas_device_class=SensorDeviceClass.GAS,
        water_device_class=SensorDeviceClass.WATER,
        suggested_display_precision=1,
        value_fn=lambda data: data.monthly_projection,
    ),
    MeterSensorDescription(
        key="yearly_projection",
        translation_key="yearly_projection",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        gas_device_class=SensorDeviceClass.GAS,
        water_device_class=SensorDeviceClass.WATER,
        suggested_display_precision=1,
        value_fn=lambda data: data.yearly_projection,
    ),
    # --- Cost Sensors ---
    MeterSensorDescription(
        key="current_price",
        translation_key="current_price",
        device_class=SensorDeviceClass.MONETARY,
        entity_category=EntityCategory.CONFIG,
        dynamic_unit=True,
        suggested_display_precision=4,
        value_fn=lambda data: data.current_price,
    ),
    MeterSensorDescription(
        key="last_period_cost",
        translation_key="last_period_cost",
        device_class=SensorDeviceClass.MONETARY,
        dynamic_unit=True,
        suggested_display_precision=2,
        value_fn=lambda data: data.last_period_cost,
    ),
    MeterSensorDescription(
        key="monthly_projected_cost",
        translation_key="monthly_projected_cost",
        device_class=SensorDeviceClass.MONETARY,
        dynamic_unit=True,
        suggested_display_precision=2,
        value_fn=lambda data: data.monthly_projected_cost,
    ),
    MeterSensorDescription(
        key="yearly_projected_cost",
        translation_key="yearly_projected_cost",
        device_class=SensorDeviceClass.MONETARY,
        dynamic_unit=True,
        suggested_display_precision=2,
        value_fn=lambda data: data.yearly_projected_cost,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GasWaterMeterConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for a meter."""
    coordinator = entry.runtime_data
    meter_type = entry.data[CONF_METER_TYPE]

    async_add_entities(MeterSensorEntity(coordinator, description, meter_type) for description in SENSOR_DESCRIPTIONS)


class MeterSensorEntity(CoordinatorEntity[MeterCoordinator], SensorEntity):
    """A sensor entity for a gas or water meter."""

    _attr_has_entity_name = True
    entity_description: MeterSensorDescription

    def __init__(
        self,
        coordinator: MeterCoordinator,
        description: MeterSensorDescription,
        meter_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._meter_type = meter_type

        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # Set device class based on meter type
        effective_dc = _gas_water_device_class(description, meter_type)
        if effective_dc is not None:
            self._attr_device_class = effective_dc

        # Set icon based on meter type
        type_icons = ICONS.get(meter_type, {})
        icon = type_icons.get(description.key)
        if icon:
            self._attr_icon = icon

        # Device info
        device_prefix = DEVICE_NAME_PREFIX.get(meter_type, "Meter")
        meter_name = entry.data.get("meter_name", "")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"{device_prefix} - {meter_name}",
            manufacturer="Manual Entry",
            model=f"{meter_type.capitalize()} Meter",
            sw_version="0.0.1",
        )

    @property
    def native_value(self) -> StateType | datetime:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        value = self.entity_description.value_fn(self.coordinator.data)

        # TIMESTAMP device_class requires a datetime object
        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return None

        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement, handling dynamic currency units."""
        if self.entity_description.dynamic_unit and self.coordinator.data is not None:
            currency = self.coordinator.data.currency
            if self.entity_description.key == "current_price":
                return f"{currency}/m\u00b3"
            return currency
        return self.entity_description.native_unit_of_measurement

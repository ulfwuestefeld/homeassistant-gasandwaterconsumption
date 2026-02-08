"""Gas & Water Meter integration for Home Assistant."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CURRENCY,
    CONF_METER_NUMBER,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MeterCoordinator
from .ocr import is_tesseract_available, read_meter_image

_LOGGER = logging.getLogger(__name__)

type GasWaterMeterConfigEntry = ConfigEntry[MeterCoordinator]

# Service schemas
SERVICE_RECORD_READING = "record_reading"
SERVICE_SET_PRICE = "set_price"
SERVICE_READ_METER_IMAGE = "read_meter_image"

ATTR_METER_READING = "meter_reading"
ATTR_METER_NUMBER = "meter_number"
ATTR_TIMESTAMP = "timestamp"
ATTR_IMAGE = "image"
ATTR_PRICE_PER_UNIT = "price_per_unit"
ATTR_VALID_FROM = "valid_from"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"

SCHEMA_RECORD_READING = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_METER_READING): vol.Coerce(float),
        vol.Optional(ATTR_METER_NUMBER): cv.string,
        vol.Optional(ATTR_TIMESTAMP): cv.string,
        vol.Optional(ATTR_IMAGE): cv.string,
    }
)

SCHEMA_SET_PRICE = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_PRICE_PER_UNIT): vol.Coerce(float),
        vol.Optional(ATTR_VALID_FROM): cv.string,
    }
)

SCHEMA_READ_METER_IMAGE = vol.Schema(
    {
        vol.Required(ATTR_IMAGE): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: GasWaterMeterConfigEntry) -> bool:
    """Set up Gas & Water Meter from a config entry."""
    coordinator = MeterCoordinator(hass, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (only once per domain)
    if not hass.services.has_service(DOMAIN, SERVICE_RECORD_READING):
        _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: GasWaterMeterConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove services if last entry
    if not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_RECORD_READING)
        hass.services.async_remove(DOMAIN, SERVICE_SET_PRICE)
        hass.services.async_remove(DOMAIN, SERVICE_READ_METER_IMAGE)

    return unload_ok


def _get_coordinator(hass: HomeAssistant, entry_id: str) -> MeterCoordinator:
    """Get the coordinator for a config entry ID."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
        )
    if not hasattr(entry, "runtime_data") or entry.runtime_data is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
        )
    return entry.runtime_data


async def _handle_record_reading(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the record_reading service call."""
    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
    coordinator = _get_coordinator(hass, entry_id)
    store = coordinator.store

    meter_reading: float | None = call.data.get(ATTR_METER_READING)
    meter_number: str | None = call.data.get(ATTR_METER_NUMBER)
    timestamp_str: str | None = call.data.get(ATTR_TIMESTAMP)
    image_path: str | None = call.data.get(ATTR_IMAGE)

    # Default timestamp to now
    if timestamp_str is None:
        timestamp_str = datetime.now(tz=UTC).isoformat()

    # Default meter number from config
    entry = hass.config_entries.async_get_entry(entry_id)
    if meter_number is None and entry is not None:
        meter_number = entry.data.get(CONF_METER_NUMBER, "")

    # Handle image and OCR
    saved_image_path: str | None = None
    if image_path is not None:
        saved_image_path = await _save_and_validate_image(hass, store, entry_id, image_path, timestamp_str)

        # Attempt OCR if meter_reading not provided
        if meter_reading is None:
            meter_reading, meter_number = await _extract_ocr(hass, image_path, meter_number)

    # Validate meter_reading is provided at this point
    if meter_reading is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="reading_required",
        )

    # Validate reading >= last reading
    last = store.get_last_reading()
    if last is not None and meter_reading < last["reading"]:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="reading_decreased",
        )

    # Store the reading
    await store.async_add_reading(
        reading=meter_reading,
        meter_number=meter_number or "",
        timestamp=timestamp_str,
        image_path=saved_image_path,
    )

    # Refresh coordinator
    await coordinator.async_request_refresh()


async def _save_and_validate_image(
    hass: HomeAssistant, store: Any, entry_id: str, image_path: str, timestamp_str: str
) -> str:
    """Validate image exists and save it to storage."""
    if not await hass.async_add_executor_job(os.path.isfile, image_path):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="image_not_found",
        )
    return await store.async_save_image(image_path, entry_id, timestamp_str)


async def _extract_ocr(
    hass: HomeAssistant, image_path: str, meter_number: str | None
) -> tuple[float | None, str | None]:
    """Run OCR to extract meter reading and optionally meter number."""
    if not is_tesseract_available():
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="ocr_unavailable",
        )

    ocr_result = await hass.async_add_executor_job(read_meter_image, image_path)

    if ocr_result.meter_reading is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="ocr_failed",
        )

    # Use OCR meter number if not provided
    if meter_number is None and ocr_result.meter_number is not None:
        meter_number = ocr_result.meter_number

    return ocr_result.meter_reading, meter_number


async def _handle_set_price(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the set_price service call."""
    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
    coordinator = _get_coordinator(hass, entry_id)

    price = call.data[ATTR_PRICE_PER_UNIT]
    valid_from: str | None = call.data.get(ATTR_VALID_FROM)

    if valid_from is None:
        valid_from = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    # Get currency from config entry
    entry = hass.config_entries.async_get_entry(entry_id)
    currency = "EUR"
    if entry is not None:
        currency = entry.data.get(CONF_CURRENCY, "EUR")

    await coordinator.store.async_add_price(
        price_per_unit=price,
        valid_from=valid_from,
        currency=currency,
    )

    # Refresh coordinator
    await coordinator.async_request_refresh()


async def _handle_read_meter_image(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Handle the read_meter_image service call."""
    image_path = call.data[ATTR_IMAGE]

    if not await hass.async_add_executor_job(os.path.isfile, image_path):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="image_not_found",
        )

    if not is_tesseract_available():
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="ocr_unavailable",
        )

    ocr_result = await hass.async_add_executor_job(read_meter_image, image_path)

    return {
        "meter_reading": ocr_result.meter_reading,
        "meter_number": ocr_result.meter_number,
        "confidence": round(ocr_result.confidence, 3),
        "raw_text": ocr_result.raw_text,
    }


def _register_services(hass: HomeAssistant) -> None:
    """Register all services for the integration."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_RECORD_READING,
        lambda call: _handle_record_reading(hass, call),
        schema=SCHEMA_RECORD_READING,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PRICE,
        lambda call: _handle_set_price(hass, call),
        schema=SCHEMA_SET_PRICE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_READ_METER_IMAGE,
        lambda call: _handle_read_meter_image(hass, call),
        schema=SCHEMA_READ_METER_IMAGE,
        supports_response=SupportsResponse.ONLY,
    )

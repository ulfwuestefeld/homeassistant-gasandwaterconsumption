"""Tests for the Gas & Water Meter service actions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from custom_components.gas_water_meter.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .conftest import MOCK_GAS_CONFIG, MOCK_STORE_DATA

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from unittest.mock import MagicMock as MockConfigEntry


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Set up a config entry for testing."""
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
        entry = MockConfigEntry(
            domain=DOMAIN,
            data=MOCK_GAS_CONFIG,
            unique_id="gas_water_meter_gas_GAS-12345",
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_record_reading_service(hass: HomeAssistant) -> None:
    """Test recording a meter reading via service."""
    entry = await _setup_entry(hass)

    with patch(
        "custom_components.gas_water_meter.store.Store.async_save",
        new_callable=AsyncMock,
    ):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                "meter_reading": 130.0,
                "timestamp": "2026-02-15T10:00:00+00:00",
            },
            blocking=True,
        )

    # After the service call, the coordinator should have been refreshed
    coordinator = entry.runtime_data
    assert coordinator is not None


async def test_record_reading_validation_decrease(hass: HomeAssistant) -> None:
    """Test that recording a decreased reading is rejected."""
    entry = await _setup_entry(hass)

    with (
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                "meter_reading": 50.0,  # Less than last reading (125.3)
            },
            blocking=True,
        )


async def test_record_reading_requires_value(hass: HomeAssistant) -> None:
    """Test that recording without reading or image is rejected."""
    entry = await _setup_entry(hass)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                # No meter_reading and no image
            },
            blocking=True,
        )


async def test_set_price_service(hass: HomeAssistant) -> None:
    """Test setting a price via service."""
    entry = await _setup_entry(hass)

    with patch(
        "custom_components.gas_water_meter.store.Store.async_save",
        new_callable=AsyncMock,
    ):
        await hass.services.async_call(
            DOMAIN,
            "set_price",
            {
                "config_entry_id": entry.entry_id,
                "price_per_unit": 2.10,
                "valid_from": "2026-03-01",
            },
            blocking=True,
        )

    # Verify the price was added
    coordinator = entry.runtime_data
    prices = coordinator.store.prices
    assert any(p["price_per_unit"] == 2.10 for p in prices)


async def test_record_reading_with_image_ocr_unavailable(hass: HomeAssistant, mock_tesseract_unavailable) -> None:
    """Test recording with image when OCR is unavailable and no manual reading."""
    entry = await _setup_entry(hass)

    with (
        patch("os.path.isfile", return_value=True),
        patch(
            "custom_components.gas_water_meter.store.MeterStore.async_save_image",
            new_callable=AsyncMock,
            return_value="/media/gas_water_meter/test/image.jpg",
        ),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                "image": "/tmp/meter_photo.jpg",
                # No meter_reading -- should fail because OCR is unavailable
            },
            blocking=True,
        )


async def test_record_reading_with_manual_value_and_image(
    hass: HomeAssistant,
) -> None:
    """Test recording with both manual reading and image (image stored, OCR skipped)."""
    entry = await _setup_entry(hass)

    with (
        patch("os.path.isfile", return_value=True),
        patch(
            "custom_components.gas_water_meter.store.MeterStore.async_save_image",
            new_callable=AsyncMock,
            return_value="/media/gas_water_meter/test/image.jpg",
        ),
        patch(
            "custom_components.gas_water_meter.store.Store.async_save",
            new_callable=AsyncMock,
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                "meter_reading": 130.0,
                "image": "/tmp/meter_photo.jpg",
            },
            blocking=True,
        )

    # Should succeed -- manual reading provided, image just stored
    coordinator = entry.runtime_data
    assert coordinator is not None


async def test_read_meter_image_service_ocr_unavailable(hass: HomeAssistant, mock_tesseract_unavailable) -> None:
    """Test read_meter_image service when OCR is unavailable."""
    await _setup_entry(hass)

    with patch("os.path.isfile", return_value=True), pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "read_meter_image",
            {
                "image": "/tmp/meter_photo.jpg",
            },
            blocking=True,
            return_response=True,
        )


async def test_record_reading_image_not_found(hass: HomeAssistant) -> None:
    """Test recording with a non-existent image file."""
    entry = await _setup_entry(hass)

    with patch("os.path.isfile", return_value=False), pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                "image": "/tmp/nonexistent.jpg",
            },
            blocking=True,
        )

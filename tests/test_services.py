"""Tests for the Gas & Water Meter service actions."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.gas_water_meter.const import DOMAIN
from custom_components.gas_water_meter.db import MeterDatabase
from custom_components.gas_water_meter.ocr import OcrResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .conftest import MOCK_GAS_CONFIG, MOCK_READINGS

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from unittest.mock import MagicMock as MockConfigEntry


async def _setup_entry(hass: HomeAssistant) -> tuple[MockConfigEntry, MeterDatabase]:
    """Set up a config entry with a real temp DB for testing."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    with patch.object(hass.config, "path", return_value=tmp_path):
        db = MeterDatabase(hass)
        await db.async_setup()

    # Pre-populate with test readings
    for r in MOCK_READINGS:
        await db.async_add_reading(
            entry_id=r["entry_id"],
            meter_number=r["meter_number"],
            reading=r["reading"],
            timestamp=r["timestamp"],
        )

    # Set up domain data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["db"] = db
    hass.data[DOMAIN]["ws_registered"] = True
    hass.data[DOMAIN]["http_registered"] = True
    hass.data[DOMAIN]["panel_registered"] = True

    # Ensure DB is closed when HA stops
    async def _close(event):
        await db.async_close()

    hass.bus.async_listen_once("homeassistant_stop", _close)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        unique_id="gas_water_meter_gas_GAS-12345",
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    return entry, db


async def test_record_reading_service(hass: HomeAssistant) -> None:
    """Test recording a meter reading via service."""
    entry, db = await _setup_entry(hass)

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

    # Verify the reading was stored
    readings = await db.async_get_readings("test_entry")
    assert any(r["reading"] == 130.0 for r in readings)


async def test_record_reading_validation_decrease(hass: HomeAssistant) -> None:
    """Test that recording a decreased reading is rejected."""
    entry, _db = await _setup_entry(hass)

    with pytest.raises(HomeAssistantError):
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
    entry, _db = await _setup_entry(hass)

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
    entry, db = await _setup_entry(hass)

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
    prices = await db.async_get_prices("test_entry")
    assert any(p["price_per_unit"] == 2.10 for p in prices)


async def test_record_reading_with_image_ocr_unavailable(hass: HomeAssistant, mock_tesseract_unavailable) -> None:
    """Test recording with image when OCR is unavailable and no manual reading."""
    entry, db = await _setup_entry(hass)

    with (
        patch("os.path.isfile", return_value=True),
        patch.object(
            db,
            "async_save_image",
            new_callable=AsyncMock,
            return_value="/media/test/image.jpg",
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
    entry, db = await _setup_entry(hass)

    with (
        patch("os.path.isfile", return_value=True),
        patch.object(
            db,
            "async_save_image",
            new_callable=AsyncMock,
            return_value="/media/test/image.jpg",
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
    _entry, _db = await _setup_entry(hass)

    with (
        patch("os.path.isfile", return_value=True),
        pytest.raises(HomeAssistantError),
    ):
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
    entry, _db = await _setup_entry(hass)

    with (
        patch("os.path.isfile", return_value=False),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                "image": "/tmp/nonexistent.jpg",
            },
            blocking=True,
        )


async def test_record_reading_default_timestamp(hass: HomeAssistant) -> None:
    """Test that a default timestamp (now) is used when none is provided."""
    entry, db = await _setup_entry(hass)

    await hass.services.async_call(
        DOMAIN,
        "record_reading",
        {
            "config_entry_id": entry.entry_id,
            "meter_reading": 130.0,
            # No timestamp provided
        },
        blocking=True,
    )

    readings = await db.async_get_readings("test_entry")
    new_reading = [r for r in readings if r["reading"] == 130.0]
    assert len(new_reading) == 1
    # Timestamp should be an ISO string (auto-generated)
    assert "T" in new_reading[0]["timestamp"]


async def test_record_reading_default_meter_number_from_config(
    hass: HomeAssistant,
) -> None:
    """Test that meter_number defaults to the config entry value when not provided."""
    entry, db = await _setup_entry(hass)

    await hass.services.async_call(
        DOMAIN,
        "record_reading",
        {
            "config_entry_id": entry.entry_id,
            "meter_reading": 130.0,
            "timestamp": "2026-02-15T10:00:00+00:00",
            # No meter_number provided -- should use GAS-12345 from config
        },
        blocking=True,
    )

    readings = await db.async_get_readings("test_entry")
    new_reading = [r for r in readings if r["reading"] == 130.0]
    assert len(new_reading) == 1
    assert new_reading[0]["meter_number"] == "GAS-12345"


async def test_record_reading_with_ocr(hass: HomeAssistant, mock_tesseract_available) -> None:
    """Test recording with image and OCR extracting the reading."""
    entry, db = await _setup_entry(hass)

    mock_ocr = OcrResult(
        meter_reading=130.5,
        meter_number="GAS-12345",
        confidence=0.95,
        raw_text="130.5",
        exif_datetime=None,
    )

    with (
        patch("os.path.isfile", return_value=True),
        patch.object(
            db,
            "async_save_image",
            new_callable=AsyncMock,
            return_value="/media/test/image.jpg",
        ),
        patch(
            "custom_components.gas_water_meter.read_meter_image",
            return_value=mock_ocr,
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                "image": "/tmp/meter_photo.jpg",
                # No meter_reading -- OCR should provide it
            },
            blocking=True,
        )

    readings = await db.async_get_readings("test_entry")
    assert any(r["reading"] == 130.5 for r in readings)


async def test_record_reading_with_exif_timestamp(hass: HomeAssistant) -> None:
    """Test that EXIF datetime from image is used when no explicit timestamp given."""
    entry, db = await _setup_entry(hass)

    with (
        patch("os.path.isfile", return_value=True),
        patch.object(
            db,
            "async_save_image",
            new_callable=AsyncMock,
            return_value="/media/test/image.jpg",
        ),
        patch(
            "custom_components.gas_water_meter.extract_exif_datetime",
            return_value="2026-02-10T15:30:00+00:00",
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": entry.entry_id,
                "meter_reading": 130.0,
                "image": "/tmp/meter_photo.jpg",
                # No timestamp -- EXIF should be used
            },
            blocking=True,
        )

    readings = await db.async_get_readings("test_entry")
    new_reading = [r for r in readings if r["reading"] == 130.0]
    assert len(new_reading) == 1
    assert new_reading[0]["timestamp"] == "2026-02-10T15:30:00+00:00"


async def test_set_price_default_valid_from(hass: HomeAssistant) -> None:
    """Test that set_price defaults valid_from to today when not provided."""
    entry, db = await _setup_entry(hass)

    await hass.services.async_call(
        DOMAIN,
        "set_price",
        {
            "config_entry_id": entry.entry_id,
            "price_per_unit": 2.50,
            # No valid_from -- should default to today
        },
        blocking=True,
    )

    prices = await db.async_get_prices("test_entry")
    new_price = [p for p in prices if p["price_per_unit"] == 2.50]
    assert len(new_price) == 1
    # valid_from should be a date string in YYYY-MM-DD format
    assert len(new_price[0]["valid_from"]) == 10


async def test_read_meter_image_returns_response(hass: HomeAssistant, mock_tesseract_available) -> None:
    """Test that read_meter_image service returns the OCR result dict."""
    _entry, _db = await _setup_entry(hass)

    mock_ocr = OcrResult(
        meter_reading=456.78,
        meter_number="GAS-99999",
        confidence=0.87654,
        raw_text="DIGITS: 456.78\n---\nFULL: Nr: GAS-99999",
        exif_datetime="2026-02-08T12:00:00",
    )

    with (
        patch("os.path.isfile", return_value=True),
        patch(
            "custom_components.gas_water_meter.read_meter_image",
            return_value=mock_ocr,
        ),
    ):
        result = await hass.services.async_call(
            DOMAIN,
            "read_meter_image",
            {"image": "/tmp/meter_photo.jpg"},
            blocking=True,
            return_response=True,
        )

    assert result["meter_reading"] == 456.78
    assert result["meter_number"] == "GAS-99999"
    assert result["confidence"] == 0.877  # rounded to 3 decimals
    assert result["exif_datetime"] == "2026-02-08T12:00:00"


async def test_set_price_with_base_fee(hass: HomeAssistant) -> None:
    """Test setting a price with base_fee via service."""
    entry, db = await _setup_entry(hass)

    await hass.services.async_call(
        DOMAIN,
        "set_price",
        {
            "config_entry_id": entry.entry_id,
            "price_per_unit": 2.10,
            "valid_from": "2026-03-01",
            "base_fee": 120.0,
        },
        blocking=True,
    )

    prices = await db.async_get_prices("test_entry")
    new_price = [p for p in prices if p["price_per_unit"] == 2.10]
    assert len(new_price) == 1
    assert new_price[0]["base_fee"] == 120.0


async def test_set_price_without_base_fee(hass: HomeAssistant) -> None:
    """Test setting a price without base_fee via service stores NULL."""
    entry, db = await _setup_entry(hass)

    await hass.services.async_call(
        DOMAIN,
        "set_price",
        {
            "config_entry_id": entry.entry_id,
            "price_per_unit": 2.20,
            "valid_from": "2026-04-01",
        },
        blocking=True,
    )

    prices = await db.async_get_prices("test_entry")
    new_price = [p for p in prices if p["price_per_unit"] == 2.20]
    assert len(new_price) == 1
    assert new_price[0]["base_fee"] is None


async def test_service_invalid_entry_id(hass: HomeAssistant) -> None:
    """Test that services reject an invalid config_entry_id."""
    _entry, _db = await _setup_entry(hass)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "record_reading",
            {
                "config_entry_id": "nonexistent_entry_id",
                "meter_reading": 100.0,
            },
            blocking=True,
        )


async def test_read_meter_image_not_found(hass: HomeAssistant) -> None:
    """Test read_meter_image service rejects non-existent image."""
    _entry, _db = await _setup_entry(hass)

    with (
        patch("os.path.isfile", return_value=False),
        pytest.raises(HomeAssistantError),
    ):
        await hass.services.async_call(
            DOMAIN,
            "read_meter_image",
            {"image": "/tmp/nonexistent.jpg"},
            blocking=True,
            return_response=True,
        )

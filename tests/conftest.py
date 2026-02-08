"""Shared fixtures for Gas & Water Meter tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from custom_components.gas_water_meter.const import (
    CONF_CURRENCY,
    CONF_METER_NAME,
    CONF_METER_NUMBER,
    CONF_METER_TYPE,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield

MOCK_GAS_CONFIG = {
    CONF_METER_TYPE: METER_TYPE_GAS,
    CONF_METER_NAME: "Kitchen",
    CONF_METER_NUMBER: "GAS-12345",
    CONF_CURRENCY: "EUR",
}

MOCK_WATER_CONFIG = {
    CONF_METER_TYPE: METER_TYPE_WATER,
    CONF_METER_NAME: "Garden",
    CONF_METER_NUMBER: "WAT-67890",
    CONF_CURRENCY: "EUR",
}

MOCK_READINGS = [
    {
        "meter_number": "GAS-12345",
        "reading": 100.0,
        "timestamp": "2026-01-01T10:00:00+00:00",
        "image_path": None,
    },
    {
        "meter_number": "GAS-12345",
        "reading": 110.5,
        "timestamp": "2026-01-15T10:00:00+00:00",
        "image_path": None,
    },
    {
        "meter_number": "GAS-12345",
        "reading": 125.3,
        "timestamp": "2026-02-01T10:00:00+00:00",
        "image_path": None,
    },
]

MOCK_PRICES = [
    {
        "price_per_unit": 1.50,
        "valid_from": "2025-01-01",
        "currency": "EUR",
    },
    {
        "price_per_unit": 1.85,
        "valid_from": "2026-01-01",
        "currency": "EUR",
    },
]

MOCK_STORE_DATA = {
    "meter_type": METER_TYPE_GAS,
    "meter_name": "Kitchen",
    "meter_number": "GAS-12345",
    "currency": "EUR",
    "readings": MOCK_READINGS,
    "prices": MOCK_PRICES,
}


@pytest.fixture
def mock_store_load():
    """Mock the Store.async_load to return test data."""
    with patch(
        "custom_components.gas_water_meter.store.Store.async_load",
        return_value=MOCK_STORE_DATA,
    ) as mock:
        yield mock


@pytest.fixture
def mock_store_save():
    """Mock the Store.async_save."""
    with patch(
        "custom_components.gas_water_meter.store.Store.async_save",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_store_empty():
    """Mock the Store.async_load to return None (empty store)."""
    with patch(
        "custom_components.gas_water_meter.store.Store.async_load",
        return_value=None,
    ) as mock:
        yield mock


@pytest.fixture
def mock_tesseract_available():
    """Mock tesseract as available."""
    with (
        patch("custom_components.gas_water_meter.ocr._TESSERACT_AVAILABLE", True),
        patch(
            "custom_components.gas_water_meter.ocr.is_tesseract_available",
            return_value=True,
        ),
    ):
        yield


@pytest.fixture
def mock_tesseract_unavailable():
    """Mock tesseract as unavailable."""
    with (
        patch("custom_components.gas_water_meter.ocr._TESSERACT_AVAILABLE", False),
        patch(
            "custom_components.gas_water_meter.ocr.is_tesseract_available",
            return_value=False,
        ),
    ):
        yield

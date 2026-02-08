"""Shared fixtures for Gas & Water Meter tests."""

from __future__ import annotations

import os
import sys
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.gas_water_meter.const import (
    CONF_CALORIFIC_VALUE,
    CONF_CONDITION_FACTOR,
    CONF_CURRENCY,
    CONF_METER_NAME,
    CONF_METER_NUMBER,
    CONF_METER_TYPE,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
)
from custom_components.gas_water_meter.db import MeterDatabase
from homeassistant.core import HomeAssistant


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


if sys.platform == "win32":
    # On Windows, the ProactorEventLoop needs real sockets for its self-pipe.
    # pytest-socket blocks socket creation which breaks event loop initialization.
    # We intercept event_loop fixture setup to re-enable sockets first.
    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_fixture_setup(fixturedef, request):
        """Re-enable sockets before event_loop fixture creates the loop."""
        if fixturedef.argname == "event_loop":
            from pytest_socket import enable_socket  # noqa: PLC0415

            enable_socket()
        yield


MOCK_GAS_CONFIG = {
    CONF_METER_TYPE: METER_TYPE_GAS,
    CONF_METER_NAME: "Kitchen",
    CONF_METER_NUMBER: "GAS-12345",
    CONF_CURRENCY: "EUR",
    CONF_CALORIFIC_VALUE: 11.465,
    CONF_CONDITION_FACTOR: 0.9684,
}

MOCK_WATER_CONFIG = {
    CONF_METER_TYPE: METER_TYPE_WATER,
    CONF_METER_NAME: "Garden",
    CONF_METER_NUMBER: "WAT-67890",
    CONF_CURRENCY: "EUR",
}

MOCK_READINGS = [
    {
        "entry_id": "test_entry",
        "meter_number": "GAS-12345",
        "reading": 100.0,
        "timestamp": "2026-01-01T10:00:00+00:00",
        "image_path": None,
    },
    {
        "entry_id": "test_entry",
        "meter_number": "GAS-12345",
        "reading": 110.5,
        "timestamp": "2026-01-15T10:00:00+00:00",
        "image_path": None,
    },
    {
        "entry_id": "test_entry",
        "meter_number": "GAS-12345",
        "reading": 125.3,
        "timestamp": "2026-02-01T10:00:00+00:00",
        "image_path": None,
    },
]

MOCK_PRICES = [
    {
        "entry_id": "test_entry",
        "price_per_unit": 1.50,
        "valid_from": "2025-01-01",
        "valid_to": "2025-12-31",
        "currency": "EUR",
    },
    {
        "entry_id": "test_entry",
        "price_per_unit": 1.85,
        "valid_from": "2026-01-01",
        "valid_to": None,
        "currency": "EUR",
    },
]

# Legacy format for migration testing
MOCK_LEGACY_STORE_DATA = {
    "meter_type": METER_TYPE_GAS,
    "meter_name": "Kitchen",
    "meter_number": "GAS-12345",
    "currency": "EUR",
    "readings": [
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
    ],
    "prices": [
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
    ],
}


@pytest.fixture
async def mock_db(hass: HomeAssistant) -> MeterDatabase:
    """Create a real MeterDatabase backed by a temp file, with test data populated."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    with patch.object(hass.config, "path", return_value=tmp_path):
        db = MeterDatabase(hass)
        await db.async_setup()

    # Populate test data
    for r in MOCK_READINGS:
        await db.async_add_reading(
            entry_id=r["entry_id"],
            meter_number=r["meter_number"],
            reading=r["reading"],
            timestamp=r["timestamp"],
            image_path=r["image_path"],
        )
    for p in MOCK_PRICES:
        await db.async_add_price(
            entry_id=p["entry_id"],
            price_per_unit=p["price_per_unit"],
            valid_from=p["valid_from"],
            valid_to=p["valid_to"],
            currency=p["currency"],
        )

    yield db

    await db.async_close()
    os.unlink(tmp_path)


@pytest.fixture
async def mock_db_empty(hass: HomeAssistant) -> MeterDatabase:
    """Create a real but empty MeterDatabase backed by a temp file."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)

    with patch.object(hass.config, "path", return_value=tmp_path):
        db = MeterDatabase(hass)
        await db.async_setup()

    yield db

    await db.async_close()
    os.unlink(tmp_path)


@pytest.fixture
def mock_setup_deps():
    """Mock panel_custom and http registration for setup tests."""
    mock_register_static = AsyncMock()
    mock_register_panel = AsyncMock()

    with (
        patch(
            "custom_components.gas_water_meter.__init__.panel_custom.async_register_panel",
            mock_register_panel,
        ),
        patch(
            "homeassistant.components.http.HomeAssistantHTTP.async_register_static_paths",
            mock_register_static,
        ),
    ):
        yield {
            "register_static": mock_register_static,
            "register_panel": mock_register_panel,
        }


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

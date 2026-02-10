"""Tests for the Gas & Water Meter WebSocket API."""

from __future__ import annotations

from custom_components.gas_water_meter.const import (
    CONF_CALORIFIC_VALUE,
    CONF_CONDITION_FACTOR,
    DOMAIN,
    METER_TYPE_GAS,
)
from custom_components.gas_water_meter.db import MeterDatabase
from custom_components.gas_water_meter.websocket import (
    ws_add_price,
    ws_add_reading,
    ws_delete_price,
    ws_delete_reading,
    ws_get_prices,
    ws_get_readings,
    ws_get_statistics,
    ws_list_meters,
    ws_update_gas_params,
    ws_update_price,
    ws_update_reading,
)
from homeassistant.core import HomeAssistant

from .conftest import MOCK_GAS_CONFIG, MOCK_WATER_CONFIG

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from unittest.mock import MagicMock as MockConfigEntry


class MockWSConnection:
    """Minimal mock for a WebSocket ActiveConnection."""

    def __init__(self) -> None:
        self.last_msg_id: int | None = None
        self.last_result: dict | None = None
        self.last_error: tuple[str, str] | None = None

    def send_result(self, msg_id: int, result: dict) -> None:
        self.last_msg_id = msg_id
        self.last_result = result

    def send_error(self, msg_id: int, code: str, message: str) -> None:
        self.last_msg_id = msg_id
        self.last_error = (code, message)


# Unwrap the decorator layers to call the async functions directly.
_ws_list_meters = ws_list_meters.__wrapped__
_ws_get_readings = ws_get_readings.__wrapped__
_ws_add_reading = ws_add_reading.__wrapped__
_ws_update_reading = ws_update_reading.__wrapped__
_ws_delete_reading = ws_delete_reading.__wrapped__
_ws_get_prices = ws_get_prices.__wrapped__
_ws_add_price = ws_add_price.__wrapped__
_ws_update_price = ws_update_price.__wrapped__
_ws_delete_price = ws_delete_price.__wrapped__
_ws_get_statistics = ws_get_statistics.__wrapped__
_ws_update_gas_params = ws_update_gas_params.__wrapped__


def _setup_db(hass: HomeAssistant, db: MeterDatabase) -> None:
    """Register DB in hass.data so WS commands can find it."""
    hass.data.setdefault(DOMAIN, {})["db"] = db


# ===================================================================
# list_meters (existing tests kept)
# ===================================================================


async def test_list_meters_returns_entry_title(hass: HomeAssistant) -> None:
    """Test that list_meters uses entry.title as the meter name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Kitchen (Gas)",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_list_meters(hass, conn, {"id": 1, "type": f"{DOMAIN}/list_meters"})

    assert conn.last_result is not None
    meters = conn.last_result["meters"]
    assert len(meters) == 1
    assert meters[0]["meter_name"] == "Kitchen (Gas)"


async def test_list_meters_reflects_renamed_entry(hass: HomeAssistant) -> None:
    """Test that list_meters shows the renamed title after a config entry rename."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Kitchen (Gas)",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    hass.config_entries.async_update_entry(entry, title="5222961 (Gas)")

    conn = MockWSConnection()
    await _ws_list_meters(hass, conn, {"id": 1, "type": f"{DOMAIN}/list_meters"})

    meters = conn.last_result["meters"]
    assert len(meters) == 1
    assert meters[0]["meter_name"] == "5222961 (Gas)"


async def test_list_meters_title_not_from_data(hass: HomeAssistant) -> None:
    """Test that renaming the entry decouples meter_name from entry.data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Original Name (Gas)",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    hass.config_entries.async_update_entry(entry, title="Renamed Meter")

    conn = MockWSConnection()
    await _ws_list_meters(hass, conn, {"id": 1, "type": f"{DOMAIN}/list_meters"})

    meter = conn.last_result["meters"][0]
    assert meter["meter_name"] == "Renamed Meter"
    assert entry.data["meter_name"] == "Kitchen"


async def test_list_meters_multiple_meters_with_renamed_titles(
    hass: HomeAssistant,
) -> None:
    """Test that all meters reflect their individual renamed titles."""
    gas_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="5222961 (Gas)",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    gas_entry.add_to_hass(hass)

    water_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_WATER_CONFIG,
        title="8EMTB123501226 (Water)",
        unique_id="gas_water_meter_water_WAT-67890",
    )
    water_entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_list_meters(hass, conn, {"id": 1, "type": f"{DOMAIN}/list_meters"})

    meters = conn.last_result["meters"]
    assert len(meters) == 2

    names = {m["meter_name"] for m in meters}
    assert "5222961 (Gas)" in names
    assert "8EMTB123501226 (Water)" in names


async def test_list_meters_includes_meter_type_and_number(hass: HomeAssistant) -> None:
    """Test that list_meters returns the correct meter type, number, and currency."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="My Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_list_meters(hass, conn, {"id": 1, "type": f"{DOMAIN}/list_meters"})

    meter = conn.last_result["meters"][0]
    assert meter["meter_type"] == METER_TYPE_GAS
    assert meter["meter_number"] == MOCK_GAS_CONFIG["meter_number"]
    assert meter["currency"] == MOCK_GAS_CONFIG["currency"]
    assert meter["entry_id"] == entry.entry_id


async def test_list_meters_gas_includes_conversion_factors(hass: HomeAssistant) -> None:
    """Test that gas meters include calorific_value and condition_factor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_list_meters(hass, conn, {"id": 1, "type": f"{DOMAIN}/list_meters"})

    meter = conn.last_result["meters"][0]
    assert "calorific_value" in meter
    assert "condition_factor" in meter
    assert meter["calorific_value"] == MOCK_GAS_CONFIG["calorific_value"]
    assert meter["condition_factor"] == MOCK_GAS_CONFIG["condition_factor"]


async def test_list_meters_water_no_conversion_factors(hass: HomeAssistant) -> None:
    """Test that water meters do not include gas-specific conversion factors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_WATER_CONFIG,
        title="Water Meter",
        unique_id="gas_water_meter_water_WAT-67890",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_list_meters(hass, conn, {"id": 1, "type": f"{DOMAIN}/list_meters"})

    meter = conn.last_result["meters"][0]
    assert "calorific_value" not in meter
    assert "condition_factor" not in meter


# ===================================================================
# get_readings
# ===================================================================


async def test_get_readings(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that get_readings returns readings and total count."""
    _setup_db(hass, mock_db)
    conn = MockWSConnection()
    await _ws_get_readings(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/get_readings", "entry_id": "test_entry", "offset": 0},
    )
    assert conn.last_result is not None
    assert len(conn.last_result["readings"]) == 3
    assert conn.last_result["total"] == 3


async def test_get_readings_pagination(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that get_readings supports limit and offset."""
    _setup_db(hass, mock_db)
    conn = MockWSConnection()
    await _ws_get_readings(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/get_readings",
            "entry_id": "test_entry",
            "limit": 2,
            "offset": 0,
        },
    )
    assert len(conn.last_result["readings"]) == 2
    assert conn.last_result["total"] == 3


async def test_get_readings_empty(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that get_readings returns empty list for unknown entry."""
    _setup_db(hass, mock_db_empty)
    conn = MockWSConnection()
    await _ws_get_readings(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/get_readings", "entry_id": "nonexistent", "offset": 0},
    )
    assert conn.last_result["readings"] == []
    assert conn.last_result["total"] == 0


# ===================================================================
# add_reading
# ===================================================================


async def test_add_reading(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that add_reading stores a reading and returns the new ID."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_add_reading(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_reading",
            "entry_id": entry.entry_id,
            "reading": 123.456,
            "meter_number": "GAS-001",
            "timestamp": "2026-01-15T10:00:00Z",
        },
    )
    assert conn.last_result is not None
    assert "id" in conn.last_result
    assert conn.last_result["id"] >= 1

    # Verify it was actually stored
    readings = await mock_db_empty.async_get_readings(entry.entry_id)
    assert len(readings) == 1
    assert readings[0]["reading"] == 123.456


async def test_add_reading_default_meter_number(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that add_reading defaults meter_number from config entry."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_add_reading(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_reading",
            "entry_id": entry.entry_id,
            "reading": 100.0,
            "timestamp": "2026-01-01T10:00:00Z",
        },
    )
    assert conn.last_result is not None

    readings = await mock_db_empty.async_get_readings(entry.entry_id)
    assert readings[0]["meter_number"] == "GAS-12345"


async def test_add_reading_default_timestamp(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that add_reading defaults timestamp to now if omitted."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_add_reading(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_reading",
            "entry_id": entry.entry_id,
            "reading": 100.0,
            "meter_number": "GAS-001",
        },
    )
    assert conn.last_result is not None

    readings = await mock_db_empty.async_get_readings(entry.entry_id)
    assert readings[0]["timestamp"] is not None
    assert "T" in readings[0]["timestamp"]  # ISO format


async def test_add_reading_with_image_path(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that add_reading stores the image_path."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_add_reading(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_reading",
            "entry_id": entry.entry_id,
            "reading": 200.0,
            "meter_number": "GAS-001",
            "timestamp": "2026-02-01T10:00:00Z",
            "image_path": "/media/gas_water_meter/photo.jpg",
        },
    )
    readings = await mock_db_empty.async_get_readings(entry.entry_id)
    assert readings[0]["image_path"] == "/media/gas_water_meter/photo.jpg"


# ===================================================================
# update_reading
# ===================================================================


async def test_update_reading(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that update_reading modifies a reading."""
    _setup_db(hass, mock_db)
    readings = await mock_db.async_get_readings("test_entry")
    reading_id = readings[0]["id"]

    conn = MockWSConnection()
    await _ws_update_reading(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_reading",
            "reading_id": reading_id,
            "reading": 999.999,
        },
    )
    assert conn.last_result == {"success": True}

    updated = await mock_db.async_get_readings("test_entry")
    target = next(r for r in updated if r["id"] == reading_id)
    assert target["reading"] == 999.999


async def test_update_reading_with_image_path(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that update_reading can add an image_path to an existing reading."""
    _setup_db(hass, mock_db)
    readings = await mock_db.async_get_readings("test_entry")
    reading_id = readings[0]["id"]

    conn = MockWSConnection()
    await _ws_update_reading(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_reading",
            "reading_id": reading_id,
            "image_path": "/media/gas_water_meter/new_photo.jpg",
        },
    )
    assert conn.last_result == {"success": True}

    updated = await mock_db.async_get_readings("test_entry")
    target = next(r for r in updated if r["id"] == reading_id)
    assert target["image_path"] == "/media/gas_water_meter/new_photo.jpg"


async def test_update_reading_not_found(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that update_reading returns error for nonexistent reading."""
    _setup_db(hass, mock_db)
    conn = MockWSConnection()
    await _ws_update_reading(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_reading",
            "reading_id": 99999,
            "reading": 1.0,
        },
    )
    assert conn.last_error is not None
    assert conn.last_error[0] == "not_found"


# ===================================================================
# delete_reading
# ===================================================================


async def test_delete_reading(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that delete_reading removes a reading."""
    _setup_db(hass, mock_db)
    readings = await mock_db.async_get_readings("test_entry")
    reading_id = readings[0]["id"]
    initial_count = len(readings)

    conn = MockWSConnection()
    await _ws_delete_reading(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/delete_reading", "reading_id": reading_id},
    )
    assert conn.last_result == {"success": True}

    remaining = await mock_db.async_get_readings("test_entry")
    assert len(remaining) == initial_count - 1


async def test_delete_reading_not_found(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that delete_reading returns error for nonexistent reading."""
    _setup_db(hass, mock_db)
    conn = MockWSConnection()
    await _ws_delete_reading(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/delete_reading", "reading_id": 99999},
    )
    assert conn.last_error is not None
    assert conn.last_error[0] == "not_found"


# ===================================================================
# get_prices
# ===================================================================


async def test_get_prices(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that get_prices returns prices for an entry."""
    _setup_db(hass, mock_db)
    conn = MockWSConnection()
    await _ws_get_prices(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/get_prices", "entry_id": "test_entry"},
    )
    assert conn.last_result is not None
    assert len(conn.last_result["prices"]) == 2


async def test_get_prices_empty(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that get_prices returns empty list for unknown entry."""
    _setup_db(hass, mock_db_empty)
    conn = MockWSConnection()
    await _ws_get_prices(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/get_prices", "entry_id": "nonexistent"},
    )
    assert conn.last_result["prices"] == []


# ===================================================================
# add_price
# ===================================================================


async def test_add_price(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that add_price stores a price and returns the new ID."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_add_price(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_price",
            "entry_id": entry.entry_id,
            "price_per_unit": 8.45,
            "valid_from": "2026-01-01",
        },
    )
    assert conn.last_result is not None
    assert "id" in conn.last_result

    prices = await mock_db_empty.async_get_prices(entry.entry_id)
    assert len(prices) == 1
    assert prices[0]["price_per_unit"] == 8.45


async def test_add_price_default_currency(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that add_price defaults currency from config entry."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_add_price(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_price",
            "entry_id": entry.entry_id,
            "price_per_unit": 1.50,
            "valid_from": "2026-01-01",
        },
    )
    prices = await mock_db_empty.async_get_prices(entry.entry_id)
    assert prices[0]["currency"] == "EUR"


# ===================================================================
# update_price
# ===================================================================


async def test_update_price(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that update_price modifies a price."""
    _setup_db(hass, mock_db)
    prices = await mock_db.async_get_prices("test_entry")
    price_id = prices[0]["id"]

    conn = MockWSConnection()
    await _ws_update_price(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_price",
            "price_id": price_id,
            "price_per_unit": 2.50,
        },
    )
    assert conn.last_result == {"success": True}

    updated = await mock_db.async_get_prices("test_entry")
    target = next(p for p in updated if p["id"] == price_id)
    assert target["price_per_unit"] == 2.50


async def test_update_price_not_found(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that update_price returns error for nonexistent price."""
    _setup_db(hass, mock_db)
    conn = MockWSConnection()
    await _ws_update_price(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_price",
            "price_id": 99999,
            "price_per_unit": 1.0,
        },
    )
    assert conn.last_error is not None
    assert conn.last_error[0] == "not_found"


# ===================================================================
# delete_price
# ===================================================================


async def test_delete_price(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that delete_price removes a price."""
    _setup_db(hass, mock_db)
    prices = await mock_db.async_get_prices("test_entry")
    price_id = prices[0]["id"]
    initial_count = len(prices)

    conn = MockWSConnection()
    await _ws_delete_price(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/delete_price", "price_id": price_id},
    )
    assert conn.last_result == {"success": True}

    remaining = await mock_db.async_get_prices("test_entry")
    assert len(remaining) == initial_count - 1


async def test_delete_price_not_found(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that delete_price returns error for nonexistent price."""
    _setup_db(hass, mock_db)
    conn = MockWSConnection()
    await _ws_delete_price(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/delete_price", "price_id": 99999},
    )
    assert conn.last_error is not None
    assert conn.last_error[0] == "not_found"


# ===================================================================
# get_statistics
# ===================================================================


async def test_get_statistics(hass: HomeAssistant, mock_db: MeterDatabase) -> None:
    """Test that get_statistics returns consumption statistics."""
    _setup_db(hass, mock_db)
    conn = MockWSConnection()
    await _ws_get_statistics(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/get_statistics", "entry_id": "test_entry"},
    )
    assert conn.last_result is not None
    stats = conn.last_result["statistics"]
    assert len(stats) >= 2  # At least 2 entries with consumption


async def test_get_statistics_empty(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that get_statistics returns empty list for unknown entry."""
    _setup_db(hass, mock_db_empty)
    conn = MockWSConnection()
    await _ws_get_statistics(
        hass,
        conn,
        {"id": 1, "type": f"{DOMAIN}/get_statistics", "entry_id": "nonexistent"},
    )
    assert conn.last_result["statistics"] == []


# ===================================================================
# update_gas_params
# ===================================================================


async def test_add_price_with_base_fee(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that ws_add_price stores base_fee when provided."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_WATER_CONFIG,
        title="Water Meter",
        unique_id="gas_water_meter_water_WAT-67890",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_add_price(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_price",
            "entry_id": entry.entry_id,
            "price_per_unit": 2.50,
            "valid_from": "2026-01-01",
            "base_fee": 120.0,
        },
    )
    assert conn.last_result is not None
    assert "id" in conn.last_result

    prices = await mock_db_empty.async_get_prices(entry.entry_id)
    assert len(prices) == 1
    assert prices[0]["base_fee"] == 120.0


async def test_add_price_without_base_fee(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that ws_add_price stores NULL base_fee when not provided."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_WATER_CONFIG,
        title="Water Meter",
        unique_id="gas_water_meter_water_WAT-67890",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_add_price(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_price",
            "entry_id": entry.entry_id,
            "price_per_unit": 2.50,
            "valid_from": "2026-01-01",
        },
    )
    prices = await mock_db_empty.async_get_prices(entry.entry_id)
    assert prices[0]["base_fee"] is None


async def test_update_price_with_base_fee(hass: HomeAssistant, mock_db_empty: MeterDatabase) -> None:
    """Test that ws_update_price can set and clear base_fee."""
    _setup_db(hass, mock_db_empty)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_WATER_CONFIG,
        title="Water Meter",
        unique_id="gas_water_meter_water_WAT-67890",
    )
    entry.add_to_hass(hass)

    # Add a price first
    conn = MockWSConnection()
    await _ws_add_price(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/add_price",
            "entry_id": entry.entry_id,
            "price_per_unit": 2.50,
            "valid_from": "2026-01-01",
        },
    )
    prices = await mock_db_empty.async_get_prices(entry.entry_id)
    price_id = prices[0]["id"]

    # Update with base_fee
    conn = MockWSConnection()
    await _ws_update_price(
        hass,
        conn,
        {
            "id": 2,
            "type": f"{DOMAIN}/update_price",
            "price_id": price_id,
            "base_fee": 96.0,
        },
    )
    assert conn.last_result == {"success": True}

    prices = await mock_db_empty.async_get_prices(entry.entry_id)
    assert prices[0]["base_fee"] == 96.0

    # Clear base_fee
    conn = MockWSConnection()
    await _ws_update_price(
        hass,
        conn,
        {
            "id": 3,
            "type": f"{DOMAIN}/update_price",
            "price_id": price_id,
            "base_fee": None,
        },
    )
    assert conn.last_result == {"success": True}

    prices = await mock_db_empty.async_get_prices(entry.entry_id)
    assert prices[0]["base_fee"] is None


async def test_update_gas_params(hass: HomeAssistant) -> None:
    """Test that update_gas_params updates calorific_value and condition_factor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_update_gas_params(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_gas_params",
            "entry_id": entry.entry_id,
            "calorific_value": 10.5,
            "condition_factor": 0.95,
        },
    )
    assert conn.last_result == {"success": True}

    # Verify the config entry was updated
    updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated_entry.data[CONF_CALORIFIC_VALUE] == 10.5
    assert updated_entry.data[CONF_CONDITION_FACTOR] == 0.95


async def test_update_gas_params_partial(hass: HomeAssistant) -> None:
    """Test that update_gas_params can update only one field."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_GAS_CONFIG,
        title="Gas Meter",
        unique_id="gas_water_meter_gas_GAS-12345",
    )
    entry.add_to_hass(hass)

    original_condition = entry.data[CONF_CONDITION_FACTOR]

    conn = MockWSConnection()
    await _ws_update_gas_params(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_gas_params",
            "entry_id": entry.entry_id,
            "calorific_value": 12.0,
        },
    )
    assert conn.last_result == {"success": True}

    updated = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated.data[CONF_CALORIFIC_VALUE] == 12.0
    assert updated.data[CONF_CONDITION_FACTOR] == original_condition


async def test_update_gas_params_non_gas_meter(hass: HomeAssistant) -> None:
    """Test that update_gas_params returns error for water meters."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_WATER_CONFIG,
        title="Water Meter",
        unique_id="gas_water_meter_water_WAT-67890",
    )
    entry.add_to_hass(hass)

    conn = MockWSConnection()
    await _ws_update_gas_params(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_gas_params",
            "entry_id": entry.entry_id,
            "calorific_value": 10.0,
        },
    )
    assert conn.last_error is not None
    assert conn.last_error[0] == "not_gas"


async def test_update_gas_params_entry_not_found(hass: HomeAssistant) -> None:
    """Test that update_gas_params returns error for nonexistent entry."""
    conn = MockWSConnection()
    await _ws_update_gas_params(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/update_gas_params",
            "entry_id": "nonexistent_entry_id",
            "calorific_value": 10.0,
        },
    )
    assert conn.last_error is not None
    assert conn.last_error[0] == "not_found"

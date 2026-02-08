"""WebSocket API for Gas & Water Meter integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import CONF_CURRENCY, CONF_METER_NAME, CONF_METER_NUMBER, CONF_METER_TYPE, DOMAIN
from .db import MeterDatabase

_LOGGER = logging.getLogger(__name__)

WS_PREFIX = f"{DOMAIN}/"


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register all WebSocket commands."""
    websocket_api.async_register_command(hass, ws_list_meters)
    websocket_api.async_register_command(hass, ws_get_readings)
    websocket_api.async_register_command(hass, ws_add_reading)
    websocket_api.async_register_command(hass, ws_update_reading)
    websocket_api.async_register_command(hass, ws_delete_reading)
    websocket_api.async_register_command(hass, ws_get_prices)
    websocket_api.async_register_command(hass, ws_add_price)
    websocket_api.async_register_command(hass, ws_update_price)
    websocket_api.async_register_command(hass, ws_delete_price)
    websocket_api.async_register_command(hass, ws_get_statistics)


def _get_db(hass: HomeAssistant) -> MeterDatabase:
    """Get the shared database instance."""
    return hass.data[DOMAIN]["db"]


# ------------------------------------------------------------------
# list_meters
# ------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}list_meters",
    }
)
@websocket_api.async_response
async def ws_list_meters(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return all configured meters with metadata."""
    meters: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        meters.append(
            {
                "entry_id": entry.entry_id,
                "meter_type": entry.data.get(CONF_METER_TYPE, ""),
                "meter_name": entry.data.get(CONF_METER_NAME, ""),
                "meter_number": entry.data.get(CONF_METER_NUMBER, ""),
                "currency": entry.data.get(CONF_CURRENCY, "EUR"),
            }
        )
    connection.send_result(msg["id"], {"meters": meters})


# ------------------------------------------------------------------
# Readings
# ------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}get_readings",
        vol.Required("entry_id"): str,
        vol.Optional("limit"): int,
        vol.Optional("offset", default=0): int,
    }
)
@websocket_api.async_response
async def ws_get_readings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return readings for a meter."""
    db = _get_db(hass)
    entry_id = msg["entry_id"]
    limit = msg.get("limit")
    offset = msg.get("offset", 0)
    readings = await db.async_get_readings(entry_id, limit=limit, offset=offset)
    total = await db.async_get_reading_count(entry_id)
    connection.send_result(msg["id"], {"readings": readings, "total": total})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}add_reading",
        vol.Required("entry_id"): str,
        vol.Required("reading"): vol.Coerce(float),
        vol.Optional("meter_number"): str,
        vol.Optional("timestamp"): str,
        vol.Optional("image_path"): str,
    }
)
@websocket_api.async_response
async def ws_add_reading(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add a new reading."""
    from datetime import UTC, datetime  # noqa: PLC0415

    db = _get_db(hass)
    entry_id = msg["entry_id"]

    # Default meter_number from config entry
    meter_number = msg.get("meter_number")
    if meter_number is None:
        entry = hass.config_entries.async_get_entry(entry_id)
        meter_number = entry.data.get(CONF_METER_NUMBER, "") if entry else ""

    # Default timestamp to now
    timestamp = msg.get("timestamp") or datetime.now(tz=UTC).isoformat()

    reading_id = await db.async_add_reading(
        entry_id=entry_id,
        meter_number=meter_number,
        reading=msg["reading"],
        timestamp=timestamp,
        image_path=msg.get("image_path"),
    )

    # Refresh the coordinator
    await _refresh_coordinator(hass, entry_id)

    connection.send_result(msg["id"], {"id": reading_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}update_reading",
        vol.Required("reading_id"): int,
        vol.Optional("meter_number"): str,
        vol.Optional("reading"): vol.Coerce(float),
        vol.Optional("timestamp"): str,
    }
)
@websocket_api.async_response
async def ws_update_reading(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update an existing reading."""
    db = _get_db(hass)
    kwargs: dict[str, Any] = {}
    if "meter_number" in msg:
        kwargs["meter_number"] = msg["meter_number"]
    if "reading" in msg:
        kwargs["reading"] = msg["reading"]
    if "timestamp" in msg:
        kwargs["timestamp"] = msg["timestamp"]

    ok = await db.async_update_reading(msg["reading_id"], **kwargs)
    if not ok:
        connection.send_error(msg["id"], "not_found", "Reading not found")
        return

    # Find which entry this reading belongs to and refresh
    await _refresh_all_coordinators(hass)

    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}delete_reading",
        vol.Required("reading_id"): int,
    }
)
@websocket_api.async_response
async def ws_delete_reading(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a reading."""
    db = _get_db(hass)
    ok = await db.async_delete_reading(msg["reading_id"])
    if not ok:
        connection.send_error(msg["id"], "not_found", "Reading not found")
        return

    await _refresh_all_coordinators(hass)
    connection.send_result(msg["id"], {"success": True})


# ------------------------------------------------------------------
# Prices
# ------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}get_prices",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_get_prices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return prices for a meter."""
    db = _get_db(hass)
    prices = await db.async_get_prices(msg["entry_id"])
    connection.send_result(msg["id"], {"prices": prices})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}add_price",
        vol.Required("entry_id"): str,
        vol.Required("price_per_unit"): vol.Coerce(float),
        vol.Required("valid_from"): str,
        vol.Optional("valid_to"): vol.Any(str, None),
        vol.Optional("currency"): str,
    }
)
@websocket_api.async_response
async def ws_add_price(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Add a new price."""
    db = _get_db(hass)
    entry_id = msg["entry_id"]

    # Default currency from config entry
    currency = msg.get("currency")
    if currency is None:
        entry = hass.config_entries.async_get_entry(entry_id)
        currency = entry.data.get(CONF_CURRENCY, "EUR") if entry else "EUR"

    price_id = await db.async_add_price(
        entry_id=entry_id,
        price_per_unit=msg["price_per_unit"],
        valid_from=msg["valid_from"],
        valid_to=msg.get("valid_to"),
        currency=currency,
    )

    await _refresh_coordinator(hass, entry_id)
    connection.send_result(msg["id"], {"id": price_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}update_price",
        vol.Required("price_id"): int,
        vol.Optional("price_per_unit"): vol.Coerce(float),
        vol.Optional("valid_from"): str,
        vol.Optional("valid_to"): vol.Any(str, None),
        vol.Optional("currency"): str,
    }
)
@websocket_api.async_response
async def ws_update_price(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update an existing price."""
    db = _get_db(hass)
    kwargs: dict[str, Any] = {}
    for key in ("price_per_unit", "valid_from", "valid_to", "currency"):
        if key in msg:
            kwargs[key] = msg[key]

    ok = await db.async_update_price(msg["price_id"], **kwargs)
    if not ok:
        connection.send_error(msg["id"], "not_found", "Price not found")
        return

    await _refresh_all_coordinators(hass)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}delete_price",
        vol.Required("price_id"): int,
    }
)
@websocket_api.async_response
async def ws_delete_price(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a price."""
    db = _get_db(hass)
    ok = await db.async_delete_price(msg["price_id"])
    if not ok:
        connection.send_error(msg["id"], "not_found", "Price not found")
        return

    await _refresh_all_coordinators(hass)
    connection.send_result(msg["id"], {"success": True})


# ------------------------------------------------------------------
# Statistics
# ------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{WS_PREFIX}get_statistics",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_get_statistics(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return consumption statistics for charting."""
    db = _get_db(hass)
    stats = await db.async_get_consumption_stats(msg["entry_id"])
    connection.send_result(msg["id"], {"statistics": stats})


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


async def _refresh_coordinator(hass: HomeAssistant, entry_id: str) -> None:
    """Refresh the coordinator for one entry."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry and hasattr(entry, "runtime_data") and entry.runtime_data:
        await entry.runtime_data.async_request_refresh()


async def _refresh_all_coordinators(hass: HomeAssistant) -> None:
    """Refresh coordinators for all entries (used after update/delete where entry_id is unknown)."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, "runtime_data") and entry.runtime_data:
            await entry.runtime_data.async_request_refresh()

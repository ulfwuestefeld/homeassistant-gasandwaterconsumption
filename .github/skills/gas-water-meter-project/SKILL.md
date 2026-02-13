---
name: gas-water-meter-project
description: Develop the Gas & Water Meter Home Assistant integration. Use when working on coordinator logic, sensor calculations, database operations, OCR processing, HTTP endpoints, WebSocket communication, or tests. Specific to gas_water_meter domain.
---

# Gas & Water Meter Integration - Project Skill

## Project Overview

**Integration**: `gas_water_meter` - Multi-meter energy/water tracking with OCR, database storage, price management, and real-time dashboards.

**Python**: 3.12+, async/await, type annotations
**Architecture**: Config-entry based, DataUpdateCoordinator pattern, SQLite + legacy JSON storage
**Testing**: pytest 8.0+, pytest-asyncio, 274+ test cases

## Directory Structure

```
gas-water-meter/
├── custom_components/gas_water_meter/
│   ├── __init__.py                    # Setup, coordinator, platform registration
│   ├── config_flow.py                 # Config UI (meter type, calorific values)
│   ├── const.py                       # Domain constants, meter types, platforms
│   ├── coordinator.py                 # MeterCoordinator - central data handler
│   ├── db.py                          # MeterDatabase - SQLite async operations
│   ├── http.py                        # HTTP endpoint for image uploads
│   ├── manifest.json                  # Integration metadata (v0.1.9)
│   ├── ocr.py                         # Tesseract OCR for meter readings
│   ├── sensor.py                      # 15 gas sensors + 13 water sensors
│   ├── services.yaml                  # Service definitions
│   ├── store.py                       # MeterStore - legacy JSON storage
│   ├── strings.json                   # i18n source (en/de)
│   ├── websocket.py                   # WebSocket API for frontend
│   ├── frontend/                      # TypeScript/Rollup frontend (Lit elements)
│   ├── tessdata/                      # OCR language models (deu, eng)
│   └── translations/
│       ├── de.json                    # German translations
│       └── en.json                    # English translations
├── tests/                             # 274+ test cases (pytest)
│   ├── test_config_flow.py
│   ├── test_coordinator.py
│   ├── test_db.py                     # Database tests (SQLite)
│   ├── test_http.py
│   ├── test_init.py
│   ├── test_ocr.py
│   ├── test_sensor.py
│   ├── test_services.py
│   ├── test_store.py                  # Legacy storage tests (28 tests)
│   └── test_websocket.py
└── pyproject.toml                     # Testing config, dependencies
```

## const.py - Constants & Configuration

```python
DOMAIN = "gas_water_meter"
METER_TYPE_GAS = "gas"
METER_TYPE_WATER = "water"

CONF_METER_TYPE = "meter_type"
CONF_METER_NAME = "meter_name"
CONF_METER_NUMBER = "meter_number"
CONF_CALORIFIC_VALUE = "calorific_value"
CONF_CONDITION_FACTOR = "condition_factor"
CONF_CURRENCY = "currency"

DEFAULT_CALORIFIC_VALUE_GAS = 11.0  # kWh/m³
DEFAULT_CONDITION_FACTOR = 0.95
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
DEFAULT_CURRENCY = "EUR"

PLATFORMS = [Platform.SENSOR]
```

**key-value naming note**: Follow `CONF_*` pattern for user-configurable keys, use lowercase with underscores.

## __init__.py - Integration Setup

```python
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .coordinator import MeterCoordinator
from .const import DOMAIN, PLATFORMS

type GasWaterMeterConfigEntry = ConfigEntry[MeterCoordinator]

async def async_setup_entry(
    hass: HomeAssistant, entry: GasWaterMeterConfigEntry
) -> bool:
    """Set up meter from config entry."""
    coordinator = MeterCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(
    hass: HomeAssistant, entry: GasWaterMeterConfigEntry
) -> bool:
    """Unload config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

**Pattern**: Store coordinator in `entry.runtime_data` for access in platforms.

## MeterCoordinator - Central Data Handler

Located in `coordinator.py`. Handles:
- Database/store initialization
- Periodic data updates (readings, prices, calculations)
- Energy/cost calculations for gas/water
- State caching for entities

```python
class MeterCoordinator(DataUpdateCoordinator):
    """Coordinator for meter readings and prices."""

    config_entry: GasWaterMeterConfigEntry

    def __init__(self, hass: HomeAssistant, entry: GasWaterMeterConfigEntry):
        super().__init__(
            hass, _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=300),
        )
        self._db = MeterDatabase(entry.entry_id)
        self._store = MeterStore(hass, entry.entry_id)

    async def async_config_entry_first_refresh(self) -> None:
        """Load database/store and perform first refresh."""
        await self._db.async_initialize()
        await self._store.async_load(...)
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> MeterData:
        """Fetch updated readings and prices from database."""
        readings = await self._db.async_get_readings(...)
        prices = await self._db.async_get_prices(...)
        return MeterData(readings=readings, prices=prices, ...)
```

**Key responsibility**: Provides `.data` MeterData object to all sensor entities.

## MeterDatabase - SQLite Storage (db.py)

Async SQLite operations via `aiosqlite`. Handles:
- Meter metadata management
- Reading storage with image references
- Price/tariff management
- Base fee tracking
- Schema migrations (v1, v2, v3, v4)

```python
class MeterDatabase:
    async def async_initialize(self) -> None:
        """Create/migrate database schema."""
        # Auto-creates tables on first run
        # Migrations: v1→v2 (readings table), v2→v3 (prices), v3→v4 (base_fee)

    async def async_add_reading(
        self,
        reading: float,
        meter_number: str,
        timestamp: str,
        image_path: str | None = None,
    ) -> None:
        """Add meter reading with optional image."""

    async def async_get_readings(
        self, meter_number: str, limit: int | None = None
    ) -> list[MeterReading]:
        """Retrieve readings sorted by timestamp (newest first)."""

    async def async_add_price(
        self,
        price_per_unit: float,
        valid_from: str,  # Date format: YYYY-MM-DD
        currency: str = "EUR",
        base_fee: float | None = None,
    ) -> None:
        """Record price/tariff effective date."""

    async def async_get_prices(self, meter_number: str) -> list[MeterPrice]:
        """Get prices sorted by valid_from (newest first)."""
```

**Schema**: Readings indexed by meter_number and timestamp for fast queries. Prices indexed by valid_from.

## MeterStore - Legacy JSON Storage (store.py)

Home Assistant Store wrapper for backward compatibility. Single JSON file per meter.

```python
class MeterStore:
    async def async_load(
        self,
        meter_type: str,  # "gas" or "water"
        meter_name: str,
        meter_number: str,
        currency: str,
    ) -> dict:
        """Load or initialize meter data from JSON store."""
        # Returns migration object to MeterDatabase

    async def async_add_reading(
        self, reading: float, meter_number: str, timestamp: str, image_path: str | None = None
    ) -> None:
        """Add reading to in-memory store."""

    async def async_save(self) -> None:
        """Persist store data to Home Assistant Store."""

    async def async_remove(self) -> None:
        """Delete store data."""
```

**Note**: Still supported for migration, but MeterDatabase is primary storage.

## Sensor Platform (sensor.py)

15 sensors for gas, 13 for water. Uses declarative `SensorEntityDescription` pattern.

### Gas Meter Sensors

```python
METER_READINGS:  # m³ (instantaneous)
  key="meter_reading"
  device_class=None

ENERGY_CONSUMPTION:  # kWh (last period: m³ × calorific × condition)
  key="energy_consumption"
  device_class=SensorDeviceClass.ENERGY
  state_class=SensorStateClass.TOTAL_INCREASING

ENERGY_CONSUMPTION_TOTAL:  # Total kWh (cumulative)
  key="energy_consumption_total"
  device_class=SensorDeviceClass.ENERGY
  state_class=SensorStateClass.TOTAL_INCREASING
  native_unit_of_measurement="kWh"

PRICE_PER_M3:  # EUR/m³ = (price_ct/100) × calorific × condition
  key="price_per_m3"
  device_class=SensorDeviceClass.MONETARY
  native_unit_of_measurement="EUR/m³"
  suggested_display_precision=4

CURRENT_PRICE:  # ct/kWh (gas only, from prices table)
  key="current_price"
  device_class=SensorDeviceClass.MONETARY
  native_unit_of_measurement="ct/kWh"

MONTHLY_PROJECTION:  # Projected month-end consumption
YEARLY_PROJECTION:  # Projected year-end consumption
DAILY_AVERAGE:      # Average consumption per day (consumption ÷ days_between)
```

**Calculation Pattern for Gas**:
```python
# Energy in kWh
energy_kWh = reading_m3 × calorific_value × condition_factor

# Price per m³ (EUR)
price_per_m3 = (current_price_ct / 100) × calorific_value × condition_factor

# Monthly cost (EUR)
monthly_cost = consumption_m3 × price_per_m3 + base_fee
```

**Key**: All gas sensors use the same calculation basis (calorific_value, condition_factor).

### Water Meter Sensors

13 sensors (no energy/price calculations):
- meter_reading, last_entry_date, consumption, daily_average, monthly_projection, yearly_projection, etc.
- All device_class=None (water utilities don't use standard HA device classes)

### Entity Implementation

```python
@dataclass
class MeterSensorDescription(SensorEntityDescription):
    """Sensor description with custom value function."""
    value_fn: Callable[[MeterData], float | None] | None = None
    meter_types: tuple[str, ...] = (METER_TYPE_GAS, METER_TYPE_WATER)

@dataclass
class MeterSensorEntity(CoordinatorEntity, SensorEntity):
    entity_description: MeterSensorDescription

    @property
    def native_value(self) -> float | None:
        """Get value from coordinator data."""
        if self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
```

## Config Flow (config_flow.py)

Single-step user configuration for meter setup.

```python
class GasWaterMeterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        """Handle user setup."""
        if user_input:
            await self.async_set_unique_id(f"{user_input['meter_type']}_{user_input['meter_number']}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input['meter_name'], data=user_input)
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("meter_type", default="gas"): vol.In(["gas", "water"]),
                vol.Required("meter_name"): str,
                vol.Required("meter_number"): str,
                vol.Optional("calorific_value", default=11.0): vol.Coerce(float),
                vol.Optional("condition_factor", default=0.95): vol.Coerce(float),
                vol.Optional("currency", default="EUR"): str,
            }),
        )
```

**Unique ID**: Combines meter_type + meter_number for safety.

## HTTP Endpoint (http.py)

Image upload endpoint for meter photos. Stores in Home Assistant media folder.

```python
async def handle_image_upload(request):
    """POST /api/gas_water_meter/{meter_number}/upload"""
    # Receives image, stores with metadata timestamp
    # Returns image_path for database reference
```

## OCR Processing (ocr.py)

Tesseract-based reading extraction from meter photos.

```python
class MeterOCR:
    async def async_extract_reading(self, image_path: str, language: str = "deu") -> str | None:
        """Extract meter reading from image using Tesseract."""
        # Uses tessdata/deu.traineddata or eng.traineddata
        # Returns numeric string or None if extraction fails
```

**Languages**: German (deu) and English (eng) trained data included.

## WebSocket API (websocket.py)

Real-time updates to frontend dashboard.

```python
async def handle_readings_stream(hass, connection, msg):
    """Stream readings updates to frontend."""
    # Sends meter_readings, prices, last_updated timestamps
    # Used by frontend panel for live updates
```

## Frontend (frontend-src/)

TypeScript/Lit web component for dashboard panel.

- Rollup bundler configuration
- `gas-water-meter-panel.js` - Custom panel element
- `test/` - Web component tests

## Testing (tests/)

### Test Patterns

**Database Tests** (`test_db.py`):
```python
async def test_add_reading_creates_entry(db):
    """Test reading insertion."""
    await db.async_add_reading(100.0, "GAS-123", "2026-01-01T10:00:00+00:00")
    readings = await db.async_get_readings("GAS-123")
    assert readings[0]["reading"] == 100.0
```

**Coordinator Tests** (`test_coordinator.py`):
```python
async def test_coordinator_updates_data(hass, coordinator):
    """Test data refresh cycle."""
    await coordinator.async_config_entry_first_refresh()
    assert coordinator.data.readings is not None
```

**Sensor Tests** (`test_sensor.py`):
```python
async def test_gas_sensors_created(hass, mock_entry):
    """Test sensor entity creation — expect 15 gas sensors."""
    await async_setup_entry(hass, mock_entry)
    # Verify sensor count and calculation values
```

**Store Tests** (`test_store.py` - 28 tests):
- Initialization, async load/save, reading/price operations, image handling
- Uses `AsyncMock` for async method mocking

**Fixtures** (`conftest.py`):
- `mock_hass` - Mocked Home Assistant instance
- `mock_entry` - Config entry fixture
- `coordinator` - Pre-initialized coordinator
- `db` - Database instance with cleanup

### Async Testing Notes

```python
# Use AsyncMock for async methods, NOT MagicMock
from unittest.mock import AsyncMock

mock_async_method = AsyncMock(return_value=data)
await mock_async_method()  # Works correctly

# NOT: MagicMock(return_value=data) — raises "can't use in 'await'"
```

## Version Management

Current version: **0.1.9** (as of 2026-02-13)

Tracked in:
- `manifest.json` - `version` field
- `config.yaml` - `version` field in add-on
- `pyproject.toml` - For testing environment
- `.cursorrules` - For code assistant context

Use SemVer (MAJOR.MINOR.PATCH). Update `CHANGELOG.md` on releases.

## Translations (i18n)

Source strings in `strings.json`:
- `config.step.user` - Config flow labels/descriptions
- `config.error.*` - Error messages
- `entity.sensor.*` - Sensor name translations
- `services.*` - Service descriptions

Example:
```json
{
  "entity": {
    "sensor": {
      "price_per_m3": {
        "name": "Price per m³"
      }
    }
  }
}
```

German translations in `translations/de.json`:
```json
{
  "entity": {
    "sensor": {
      "price_per_m3": {
        "name": "Preis pro m³"
      }
    }
  }
}
```

**Rule**: Never hardcode English sensor names in Python code — use `translation_key` in entity description.

## Linting & Code Quality

**Tools**: ruff (check + format), pytest, pytest-cov

```bash
# Lint check
python -m ruff check gas-water-meter/custom_components/ tests/

# Format
python -m ruff format gas-water-meter/custom_components/ tests/

# Tests with coverage
pytest tests/ --cov=gas-water-meter/custom_components/gas_water_meter

# Store tests only (28 tests)
pytest tests/test_store.py -v
```

**Current Status**: 274 tests passing, 100% ruff compliance.

## Complete Code Patterns for This Project

### MeterCoordinator Pattern (async-first, error handling)

```python
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

class MeterCoordinator(DataUpdateCoordinator[MeterData]):
    config_entry: GasWaterMeterConfigEntry

    def __init__(self, hass: HomeAssistant, entry: GasWaterMeterConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._db = MeterDatabase(entry.entry_id)
        self._store = MeterStore(hass, entry.entry_id)

    async def _async_setup(self) -> None:
        """Initialize database and store on first refresh."""
        try:
            await self._db.async_initialize()
            meter_data = await self._store.async_load(...)
        except Exception as err:
            raise ConfigEntryNotReady(f"Cannot load data: {err}") from err

    async def _async_update_data(self) -> MeterData:
        """Fetch updated readings and prices."""
        try:
            readings = await self._db.async_get_readings(meter_number)
            prices = await self._db.async_get_prices(meter_number)
            return MeterData(readings=readings, prices=prices, ...)
        except Exception as err:
            raise UpdateFailed(f"Update failed: {err}") from err
```

**Key patterns**:
- Call `await coordinator.async_config_entry_first_refresh()` in setup to trigger `_async_setup()`
- Raise `ConfigEntryNotReady` for setup failures (triggers retry)
- Raise `UpdateFailed` for transient updates (makes entities unavailable, retries later)
- Raise `ConfigEntryAuthFailed` for authentication (triggers reauth flow)

### Sensor Platform with Dynamic Filtering

```python
async def async_setup_entry(hass, entry, async_add_entities):
    """Create sensors based on meter type."""
    coordinator = entry.runtime_data
    meter_type = coordinator.config_entry.data.get("meter_type", "gas")
    
    entities = [
        MeterSensorEntity(coordinator, desc)
        for desc in METER_SENSOR_DESCRIPTIONS
        if meter_type in desc.meter_types  # Filter by meter_type
    ]
    async_add_entities(entities)
```

### Multi-Step Config Flow Pattern

```python
class GasWaterMeterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        """Manual setup."""
        errors = {}
        if user_input:
            # Validate meter number as unique ID
            await self.async_set_unique_id(
                f"{user_input['meter_type']}_{user_input['meter_number']}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input["meter_name"],
                data=user_input,
            )
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("meter_type"): vol.In([METER_TYPE_GAS, METER_TYPE_WATER]),
                vol.Required("meter_name"): str,
                vol.Required("meter_number"): str,
                vol.Optional("calorific_value", default=11.0): vol.Coerce(float),
                vol.Optional("condition_factor", default=0.95): vol.Coerce(float),
                vol.Optional("currency", default="EUR"): str,
            }),
            errors=errors,
        )
```

### Error Handling with Translated Exceptions

```python
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

# In config flow validation
try:
    meter_data = await self._db.async_get_readings(meter_number)
except Exception as err:
    errors["base"] = "cannot_load_meter"
    # Error message from strings.json config.error.cannot_load_meter
```

## Testing Best Practices for This Project

### Store Tests Pattern (AsyncMock for async methods)

```python
from unittest.mock import AsyncMock, MagicMock, patch

async def test_async_load_creates_default_data(mock_hass):
    """Test async_load initializes structure."""
    with patch("custom_components.gas_water_meter.store.Store") as mock_store_class:
        # ✓ Correct: AsyncMock for async methods
        mock_store_instance = MagicMock()
        mock_store_instance.async_load = AsyncMock(return_value=None)
        mock_store_instance.async_save = AsyncMock()
        mock_store_class.return_value = mock_store_instance

        store = MeterStore(mock_hass, "test_entry")
        await store.async_load(meter_type="gas", ...)
        
        # ✗ Wrong: Would raise "can't use in 'await' expression"
        # mock_store_instance.async_load = MagicMock(return_value=None)
```

**Critical rule**: Use `AsyncMock` for async methods, `MagicMock` for blocking methods.

### Coordinator Tests Pattern

```python
async def test_coordinator_updates_readings(hass, mock_entry):
    """Test coordinator fetches and caches readings."""
    with patch.object(MeterDatabase, "async_get_readings", 
                     return_value=MOCK_READINGS) as mock_get:
        coordinator = MeterCoordinator(hass, mock_entry)
        await coordinator.async_config_entry_first_refresh()
        
        assert coordinator.data.readings == MOCK_READINGS
        mock_get.assert_called()
```

### Sensor Entity Tests Pattern

```python
async def test_gas_sensors_created(hass, mock_entry):
    """Test 15 gas sensors are created."""
    with patch.object(MeterCoordinator, "_async_update_data",
                     return_value=MOCK_DATA):
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()
        
        # Assert all 15 gas sensors exist
        for sensor_key in GAS_SENSOR_KEYS:
            state = hass.states.get(f"sensor.gas_meter_{sensor_key}")
            assert state is not None
```

### Config Flow Tests Pattern

```python
async def test_user_flow_creates_entry(hass):
    """Test config flow creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "meter_type": "gas",
            "meter_name": "Kitchen",
            "meter_number": "GAS-12345",
            "calorific_value": 11.0,
        },
    )
    
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["meter_type"] == "gas"
```

### Running Tests with Coverage

```bash
# Run all tests
pytest tests/ -q

# With coverage report
pytest tests/ --cov=gas-water-meter/custom_components/gas_water_meter --cov-report=term-missing

# Specific test file
pytest tests/test_store.py -v

# Stop after first failure
pytest tests/ -x

# Run specific test by name pattern
pytest tests/ -k "test_gas_sensors"
```

**Current test coverage**: 274 tests, 28 new store.py tests

## Development Workflow

1. **Make changes** to coordinator, sensors, database logic
2. **Update tests** — add test case before fixing code
3. **Run tests**: `pytest tests/ -q`
4. **Format code**: `ruff format ...`
5. **Lint check**: `ruff check ...` (must pass)
6. **Update CHANGELOG.md** with summary
7. **Update version** in manifest.json + config.yaml
8. **Commit** with descriptive message

## manifest.json Reference (Full)

**Current manifest.json (v0.1.9)**:

```json
{
  "domain": "gas_water_meter",
  "name": "Gas & Water Meter",
  "codeowners": ["@your_github"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/your_repo",
  "integration_type": "service",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/your_repo/issues",
  "requirements": ["Pillow==12.0.0", "pytesseract==0.3.13"],
  "version": "0.1.9"
}
```

**Key field explanations**:
- **domain**: Unique identifier, must match directory name
- **version**: Required for custom integrations; use SemVer (MAJOR.MINOR.PATCH)
- **integration_type**: `service` = single service per config entry
- **iot_class**: `local_polling` = manually fetch readings via OCR/HTTP
- **requirements**: Only list packages NOT in HA Core (see reference.md)

## Entity Platform Configuration Reference

### Device Classes (SensorDeviceClass)

| Device Class | Use Case | Unit | State Class |
|--------------|----------|------|-------------|
| `ENERGY` | Energy consumption (kWh) | kWh | TOTAL_INCREASING |
| `MONETARY` | Price/cost | EUR/m³, ct/kWh | MEASUREMENT |
| `TEMPERATURE` | Temperature | °C/°F | MEASUREMENT |
| `BATTERY` | Battery level | % | MEASUREMENT |
| None | Raw measurements | - | MEASUREMENT |

### Entity Category

- Default (None): Primary feature of device, shown on front-end
- `EntityCategory.DIAGNOSTIC`: Secondary/debug info, hidden by default
- `EntityCategory.CONFIG`: Configuration parameter, hidden by default

### State Class (SensorStateClass)

- **MEASUREMENT**: Instantaneous value (don't reset)
- **TOTAL**: Cumulative value (monotonically increases)
- **TOTAL_INCREASING**: Can reset to 0 (utility meters)

**For this project**:
- `meter_reading`: None (raw instantaneous reading)
- `energy_consumption`: TOTAL_INCREASING (m³/kWh, can reset)
- `current_price`: MEASUREMENT (live price)
- `monthly_projection`: MEASUREMENT (calculated forecast)

## User-Facing Design for States & Attributes

### State Design Rules

Your sensor states are used by users in:
- Jinja2 templates: `{{ states('sensor.gas_meter_reading') }}`
- Automations: `{{ is_state(...) }}`
- Dashboards & cards
- Voice assistants

**Design implications**:
1. **States must be meaningful strings**: "on"/"off" or numeric values
2. **Use standard device classes**: ENERGY states should represent kWh
3. **Never use flicker**: State shouldn't change rapidly without reason
4. **Attributes for queries**: Users access via `state_attr('sensor.xxx', 'attr_name')`
5. **Translation keys**: Provide translated values in `strings.json`

**Example for gas meter**:
```python
# ✓ Good: Clear numeric state
native_value = 100.5  # User sees "100.5" m³

# ✓ Good: Binary state
native_value = "on" if online else "off"

# ✗ Bad: Flickers between states
native_value = random.choice([10.0, 10.1, 10.0])  # Confuses users

# ✗ Bad: Hardcoded English
native_value = "online" if online else "offline"  # Use translation_key instead
```

### Event Bus & State Changes

Whenever a sensor state changes, `state_changed` event fires:
```python
{
  "event_type": "state_changed",
  "data": {
    "entity_id": "sensor.gas_meter_reading",
    "old_state": {...},
    "new_state": {...},
  }
}
```

Users trigger automations on these state changes. Ensure:
- Initial state is set (not None)
- State doesn't flick rapidly
- Attribute changes trigger `last_updated`

## HACS Distribution & Community

### Repository Setup for HACS

```
your-repo/
├── custom_components/
│   └── gas_water_meter/
│       ├── __init__.py
│       ├── manifest.json          # Required: version, documentation, issue_tracker
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── db.py
│       ├── ocr.py
│       ├── sensor.py
│       └── ...
├── README.md                        # Setup instructions, entity descriptions
├── CHANGELOG.md                     # Release notes with version history
└── hacs.json (optional)             # HACS metadata
```

### hacs.json (Optional)

```json
{
  "name": "Gas & Water Meter",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
```

### Community Resources for Integration Developers

| Resource | URL | Purpose |
|----------|-----|---------|
| Developer Docs | https://developers.home-assistant.io/ | Official HA integration guide |
| User Docs | https://www.home-assistant.io/docs/ | User-facing HA docs |
| Community Forum | https://community.home-assistant.io/c/third-party/15 | Support, discussion for custom integrations |
| Discord #developers | https://discord.gg/home-assistant | Real-time developer chat |
| GitHub Brands | https://github.com/home-assistant/brands | Submit integration icons |
| Blueprint Template | https://github.com/custom-components/blueprint | Starter template for new integrations |

### Community Best Practices

1. **Create a forum topic** for your integration in [Third party integrations](https://community.home-assistant.io/c/third-party/15)
2. **Respond to issues** — active maintenance builds user trust
3. **Document breaking changes** clearly in release notes
4. **Test on HA OS** — most users run HA OS (not Docker/Core)
5. **Use SemVer** — users rely on version numbers for safe updates
6. **Add to HACS** — standard distribution method for custom integrations
7. **Submit brand assets** to [home-assistant/brands](https://github.com/home-assistant/brands) for icon

## Key Patterns for This Project

| Pattern | Usage | Example |
|---------|-------|---------|
| Async database | All DB operations | `await db.async_get_readings()` |
| Coordinator caching | Entity data access | `coordinator.data.readings` |
| Sensor descriptions | Declarative entity defs | `MeterSensorDescription(key=..., value_fn=...)` |
| Calculation functions | Gas conversions | `energy = m³ × calorific × condition` |
| Legacy store migration | Backward compatibility | `MeterStore` → `MeterDatabase` |
| Config flow validation | User input verification | `async_set_unique_id()` + `_abort_if_unique_id_configured()` |
| AsyncMock for tests | Async method mocking | `AsyncMock(return_value=...)` not `MagicMock(...)` |
| Device class design | User-facing states | ENERGY for kWh, MONETARY for EUR |
| Entity registry | Unique identification | `unique_id = f"{entry_id}_{sensor_key}"` |

## Resources

- **Home Assistant Developers**: https://developers.home-assistant.io/
- **Integration Reference**: gas_water_meter source code patterns
- **Test Template**: `tests/conftest.py` fixtures
- **Database Schema**: `db.py` class docstrings + migration logic
- **Sensor Definitions**: `sensor.py` METER_READINGS list

---

**Last Updated**: 2026-02-13  
**Maintainer**: Gas & Water Meter Team

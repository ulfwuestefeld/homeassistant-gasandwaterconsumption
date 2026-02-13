# GitHub Copilot Instructions - Gas & Water Meter Project

This file provides custom instructions for GitHub Copilot to ensure consistent code generation aligned with the project's architecture, testing standards, and Home Assistant integration patterns.

## Project Context

**Project**: Gas & Water Meter Home Assistant Add-on
**Domain**: `gas_water_meter`
**Version**: 0.1.9
**Python**: >= 3.12
**Pattern**: Async-first, config-entry-based, coordinator pattern
**Test Framework**: pytest with 274+ tests

---

## Core Development Principles

### 1. Code Generation Standards

When writing code:

- **Always include type annotations**: Use `from __future__ import annotations` at the top
- **Async-first design**: Use `async def` and `await` for all I/O operations
- **Error handling**: Raise specific exceptions (`ConfigEntryNotReady`, `ConfigEntryAuthFailed`, `UpdateFailed`)
- **Logging**: Use `logging.getLogger(__name__)` never `print()`
- **No blocking code**: Use `hass.async_add_executor_job()` for blocking operations
- **Constants**: Import from `homeassistant.const` where available, define project constants in `const.py`

### 2. Test Requirements

**Every code change must include tests:**

- Unit tests for business logic (database queries, calculations, OCR)
- Integration tests for config flow, sensors, coordinator
- Use `AsyncMock` for async methods (NOT `MagicMock`)
- Use pytest fixtures in `tests/conftest.py`
- Tests must pass: `pytest tests/ -q`
- Coverage must be maintained or improved

### 3. Home Assistant Integration Patterns

When modifying Home Assistant integration code:

- Follow the coordinator pattern (see `coordinator.py`)
- Entities must use `has_entity_name = True` (mandatory)
- All entities must have `unique_id` and `device_info`
- Use `translation_key` for entity names (no hardcoded English)
- Sensor descriptions use `SensorEntityDescription` with `value_fn` lambdas
- Config flow must validate with `async_set_unique_id()` + `_abort_if_unique_id_configured()`
- Services registered in `async_setup_entry()` (not `async_setup()`)

### 4. Database & Storage

**SQLite** (primary, `db.py`):
- All operations are async via `aiosqlite`
- Use prepared statements to prevent SQL injection
- Schema migrations handled in `async_initialize()`
- All readings indexed by `meter_number` and `timestamp`
- Prices indexed by `valid_from` date

**Legacy JSON** (store.py, migration only):
- Keep for backward compatibility
- New code should use `MeterDatabase` not `MeterStore`

### 5. Sensor Calculations (Gas Meters)

**Energy conversion**:
```python
energy_kWh = reading_m3 × calorific_value × condition_factor
```

**Price per m³**:
```python
price_per_m3 = (price_ct / 100) × calorific_value × condition_factor
```

**Cost calculations**:
- Include optional `base_fee` (pro-rated by days or months)
- `last_period_cost` = consumption × price_per_m3 + pro-rated base fee
- Monthly/yearly projections use running averages

**Important**: Calorific value and condition factor are stored **per price entry**, not globally. Config entry defaults serve as fallback for legacy data.

### 6. Gas vs Water Meter Distinctions

| Aspect | Gas | Water |
|--------|-----|-------|
| Sensors | 16 (13 common + energy_consumption + energy_consumption_total + price_per_m3) | 13 (13 common) |
| Energy calc | Yes (kWh = m³ × calorific × condition) | No |
| Device class | GAS/ENERGY, MONETARY | WATER |
| Pricing | ct/kWh (converted to EUR/m³) | EUR/m³ (direct) |
| Icons | gas symbols | water drop symbols |

### 7. Meter Number Change Detection

When `meter_number` changes between readings:
- Consumption resets (no delta calculation)
- Projections use only current meter readings
- Use `async_get_first_reading_for_meter()` to filter by meter

### 8. Code Quality & Linting

Before committing:

```bash
# Format code
python -m ruff format gas-water-meter/custom_components/ tests/

# Lint check
python -m ruff check gas-water-meter/custom_components/ tests/

# Run tests
pytest tests/ -q

# Full test with coverage
pytest tests/ --cov=gas-water-meter/custom_components/gas_water_meter --cov-report=term-missing
```

All code must pass ruff checks (0 errors).

### 9. File Structure Rules

**Never modify**:
- `Dockerfile` (unless adding system dependencies)
- `run.sh` (startup script)
- `build.yaml` (multi-arch config)

**Always update when changing**:
- `manifest.json` (version, dependencies)
- `gas-water-meter/config.yaml` (add-on version)
- `CHANGELOG.md` (both root and gas-water-meter/)
- `.cursorrules` (if architecture changes)
- `SBOM.json` / `SBOM.md` (if dependencies change)
- `FOSS.md` (if adding open source libs)
- `.github/copilot-instructions.md` (if project rules change)

### 10. Testing Patterns

**Current test count**: 274+ tests (all passing)

Key test files:
- `tests/test_db.py` - Database operations
- `tests/test_coordinator.py` - Data coordinator
- `tests/test_config_flow.py` - UI config flow
- `tests/test_sensor.py` - Sensor creation (expects 16 gas, 13 water)
- `tests/test_store.py` - Legacy storage (28 tests)
- `tests/test_ocr.py` - OCR/Tesseract
- `tests/test_http.py` - REST API
- `tests/test_websocket.py` - WebSocket API
- `tests/test_services.py` - Service actions

**Critical async testing rule**: Use `AsyncMock` for async methods:
```python
from unittest.mock import AsyncMock

# ✓ Correct
mock_method = AsyncMock(return_value=data)
await mock_method()

# ✗ Wrong - raises "can't use in 'await' expression"
mock_method = MagicMock(return_value=data)
await mock_method()
```

---

## Specific File Responsibilities

### `__init__.py`
- Integration setup and teardown
- Service registration
- Panel registration
- Coordinator initialization

### `config_flow.py`
- Multi-step user flow (meter type selection, gas parameters)
- Validation with `async_set_unique_id()`
- Error handling with translated messages

### `coordinator.py`
- Central data fetching and caching
- Projections and cost calculations
- Error states and retries

### `db.py`
- SQLite schema and migrations
- Async CRUD operations for readings, prices, meters
- Schema version: 3 (with base_fee support)

### `sensor.py`
- 16 gas sensors + 13 water sensors (13 common, 3 gas-only)
- `SensorEntityDescription` declarations with `meter_types` filter
- `value_fn` lambdas for calculations (energy, price conversions)

### `services.yaml` + service handlers
- `record_reading`: Add meter reading with optional image
- `set_price`: Set price/tariff
- `read_meter_image`: Alternative OCR image processor

### `ocr.py`
- Tesseract OCR wrapper (optional, auto-installed)
- EXIF timestamp extraction
- Image processing via Pillow

### `http.py`
- REST endpoint: POST `/api/gas_water_meter/upload_image`
- Multipart form handling (max 20 MB, 21 MP)
- Image storage in HA media folder

### `websocket.py`
- Custom WebSocket commands for frontend
- Real-time CRUD for readings, prices, meters
- Statistics endpoints

### `store.py`
- Legacy JSON storage (read-only for migration)
- Do not add new features here

### Frontend (`frontend-src/`)
- Lit elements for sidebar panel
- Chart.js for monthly visualization
- i18n via `TRANSLATIONS` dict
- Tests with Web Test Runner

---

## Translation & Internationalization

When adding new strings:

1. **Add to `strings.json`**:
```json
{
  "entity": {
    "sensor": {
      "new_sensor": {
        "name": "New Sensor Name",
        "state": { "state_value": "Translated State" }
      }
    }
  }
}
```

2. **Add to `translations/en.json`** (English translation)

3. **Add to `translations/de.json`** (German translation)

4. **In sensor code, use `translation_key`**:
```python
SensorEntityDescription(
    key="new_sensor",
    translation_key="new_sensor",  # Matches strings.json key
    ...
)
```

---

## Dependencies Management

### Always in `manifest.json`:
- `pytesseract` (for OCR, optional but recommended)
- `aiosqlite` (SQLite async)
- `pillow-heif` (HEIC/HEIF support)

### Always in HA Core (don't add to requirements):
- `aiohttp`, `requests`, `Pillow`, `Jinja2`, `PyYAML`, `cryptography`, `orjson`, `SQLAlchemy`, `voluptuous`, `zeroconf`, etc.

### When adding a dependency:
1. Add to `manifest.json` `requirements` field
2. Update `SBOM.json` and `SBOM.md`
3. Update `FOSS.md` with license info
4. Regenerate `requirements_test.txt` if needed
5. Update `gas-water-meter/Dockerfile` if system library needed

---

## Version Management

All version numbers must be synchronized:
- `manifest.json`: `"version": "X.Y.Z"`
- `gas-water-meter/config.yaml`: `version: X.Y.Z`
- `.cursorrules`: Update version reference

Update `CHANGELOG.md` for every release:
```markdown
## [0.1.9] - 2026-02-13

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Breaking change or refactor description
```

---

## Common Code Snippets

### Async Database Query
```python
async def async_get_readings(self, meter_number: str) -> list[MeterReading]:
    cursor = await self._db.execute(
        "SELECT * FROM readings WHERE meter_number = ? ORDER BY timestamp DESC",
        (meter_number,),
    )
    return await cursor.fetchall()
```

### Sensor with Calculation
```python
SensorEntityDescription(
    key="energy_consumption",
    translation_key="energy_consumption",
    device_class=SensorDeviceClass.ENERGY,
    native_unit_of_measurement="kWh",
    state_class=SensorStateClass.TOTAL_INCREASING,
    value_fn=lambda data: data.meter_reading * data.calorific_value * data.condition_factor
    if data.meter_reading and data.calorific_value and data.condition_factor else None,
)
```

### Config Flow with Validation
```python
async def async_step_user(self, user_input=None):
    if user_input:
        await self.async_set_unique_id(
            f"{user_input['meter_type']}_{user_input['meter_number']}"
        )
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input["meter_name"], data=user_input)
    # ...
```

### Coordinator with Error Handling
```python
async def _async_update_data(self) -> MeterData:
    try:
        readings = await self._db.async_get_readings(self.meter_number)
        prices = await self._db.async_get_prices(self.meter_number)
        return MeterData(readings=readings, prices=prices, ...)
    except Exception as err:
        raise UpdateFailed(f"Error: {err}") from err
```

### Async Mock in Tests
```python
from unittest.mock import AsyncMock

async def test_async_load():
    mock_store = MagicMock()
    mock_store.async_load = AsyncMock(return_value={})
    await mock_store.async_load()  # Works correctly
```

---

## When You See a Problem

1. **Linting errors**: Run `ruff check --fix` to auto-fix, or manually apply suggestions
2. **Test failures**: Run `pytest tests/test_<file>.py -vv` to debug
3. **Type annotation issues**: Add `from __future__ import annotations` and use string forward references
4. **Async/await confusion**: Ensure all `await` targets return a coroutine (use `AsyncMock`, not `MagicMock`)
5. **Version mismatches**: Use grep to find all version references and update consistently
6. **Translation missing**: Add to `strings.json`, `translations/en.json`, `translations/de.json`

---

## Quality Checklist Template

After each significant change, verify:

- [ ] All tests pass (`pytest tests/ -q`)
- [ ] Ruff checks pass (`ruff check gas-water-meter/custom_components/ tests/`)
- [ ] Ruff format applied (`ruff format gas-water-meter/custom_components/ tests/`)
- [ ] New code has unit tests
- [ ] Translations added (strings.json + de.json + en.json)
- [ ] Version updated (manifest.json, config.yaml, CHANGELOG.md)
- [ ] Dependencies documented (SBOM.json, FOSS.md if changed)
- [ ] .cursorrules still accurate
- [ ] No hardcoded English strings (use `translation_key`)
- [ ] All async operations properly awaited
- [ ] Mocks use `AsyncMock` for async methods
- [ ] Unique IDs set on all entities
- [ ] Device info populated on all entities

---

## Home Assistant Skill Integration

For Home Assistant-specific patterns, reference the `gas-water-meter-project` Cursor skill in `.github/skills/gas-water-meter-project/SKILL.md`. Key patterns documented:

- MeterCoordinator async pattern
- Sensor platform with dynamic filtering
- Multi-step config flow
- Database operations (aiosqlite)
- Testing with AsyncMock
- Error handling and translations

---

**Last Updated**: 2026-02-13
**For issues or updates to these instructions, edit `.github/copilot-instructions.md`**

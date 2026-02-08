# Changelog

All notable changes to the Gas & Water Meter project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-08

### Added

- **Meter number change detection** — when the meter number changes between consecutive readings (e.g. meter replacement), consumption resets to zero; projections are based only on the current meter's readings
- **Gas energy conversion** — gas meters now support calorific value (Brennwert, kWh/m³) and condition factor (Zustandszahl) for converting m³ to kWh
- **Energy consumption sensor** — new sensor for gas meters showing consumption in kWh (= m³ × Brennwert × Zustandszahl)
- **Gas-specific pricing** — gas prices are entered in ct/kWh; costs are calculated as: kWh × ct/kWh / 100 = EUR
- **Two-step config flow for gas** — gas meters now have a second setup step for calorific value and condition factor
- **Gas conversion factor management** — edit Brennwert and Zustandszahl via options flow, sidebar panel, or WebSocket API
- **WebSocket command `update_gas_params`** — update gas conversion factors from the frontend
- **Mobile responsive history** — card-based layout on narrow screens with touch-friendly action buttons (min 44px)
- **Photo upload from history** — upload or replace photos for existing readings directly from the history table
- **Scrollable tables** — horizontal scroll wrappers for data tables on small screens
- **Monthly consumption chart** — chart now always displays consumption aggregated by calendar month; periods spanning multiple months are distributed proportionally by days

### Changed

- Gas cost calculation: `cost = m³ × Brennwert × Zustandszahl × price(ct/kWh) / 100` (was: `m³ × price`)
- Water cost calculation unchanged: `cost = m³ × price(EUR/m³)`
- Gas meters now create 13 sensors (12 common + energy_consumption); water meters still create 12
- Price sensor unit for gas: `ct/kWh` (was: `EUR/m³`)
- Frontend price form adapts labels and units based on meter type (gas vs water)
- Projections now filter by current meter number (ignores readings from replaced meters)
- Consumption statistics chart also respects meter number boundaries
- Version bumped to 0.1.0

## [0.0.4] - 2026-02-08

### Added

- **Graphical user interface (GUI)** — new sidebar panel built with Lit for managing meters, readings, prices, and photos directly in the browser
- **SQLite database** — persistent storage migrated from JSON files to SQLite via `aiosqlite` for better performance and reliability
- **WebSocket API** — custom commands for frontend-backend communication (CRUD for readings, prices, meters, statistics)
- **REST API** — dedicated HTTP endpoint for multipart image uploads with OCR and EXIF extraction
- **Consumption chart** — Chart.js visualization of historical consumption and meter readings
- **Price validity periods** — prices now support `valid_from` and optional `valid_to` dates
- **Photo upload via GUI** — upload meter photos directly from the sidebar panel with client-side validation (max 20 MB, max 21 megapixels)
- **Automatic data migration** — existing JSON store data is automatically migrated to SQLite on first startup
- **HEIC/HEIF photo support** — upload photos in Apple HEIC/HEIF format (via `pillow-heif`); automatic conversion for OCR and EXIF extraction

### Changed

- Storage backend changed from `homeassistant.helpers.storage.Store` (JSON) to SQLite (`aiosqlite`)
- Service handlers refactored to use proper `async def` wrappers instead of lambdas
- `current_price` sensor entity category changed from `CONFIG` to `DIAGNOSTIC` (HA 2025.1+ compliance)
- `daily_average` sensor no longer uses gas/water device class (incompatible with rate unit `m³/d`)
- `panel_custom` and `http` removed from `manifest.json` dependencies (always available in HA core)
- Sidebar title changed to English ("Gas & Water Meter") for international accessibility
- Frontend panel fully internationalized (English/German) using `hass.language`

### Fixed

- Service handlers not being awaited due to lambda wrapping (readings not saved)
- Sensor entity category validation error for `current_price` sensor
- Device class / unit incompatibility for `daily_average` sensor
- EXIF datetime extraction tests using mock-based approach for reliability
- Windows test compatibility with `pytest-socket` and `ProactorEventLoop`
- Unclosed database connections in test teardown

## [0.0.3] - 2026-02-08

### Fixed

- Fixed add-on installation failure: removed `image` field from `config.yaml` (no pre-built image on ghcr.io)
- Fixed CRLF line endings in `run.sh` causing Docker execution failure on Linux
- Added `dos2unix` to Dockerfile to convert line endings at build time
- Added `.gitattributes` to enforce LF line endings for shell scripts and Dockerfiles
- Fixed architecture mismatch between `config.yaml` and `build.yaml` (removed stale `armhf`)
- Fixed missing `enable_custom_integrations` fixture in test conftest (root cause of all test failures)
- Added `custom_components` symlink step in CI workflow for HA loader discovery
- Added `.gitignore` for generated files

## [0.0.2] - 2026-02-08

### Fixed

- Fixed missing `__init__.py` in `custom_components/` package (integration was not discovered by HA)
- Fixed coordinator tests using `async_config_entry_first_refresh` outside setup flow
- Fixed OCR test where adjacent digits across newlines were incorrectly merged
- Set author/codeowner to `ulfwuestefeld` across all metadata files

## [0.0.1] - 2026-02-08

### Added

- Initial release as Home Assistant add-on (replaces HACS-based distribution)
- Add-on automatically installs custom integration into Home Assistant config
- Tesseract OCR pre-installed in add-on container
- Config flow for adding gas and water meters with name, number, and currency
- Options flow for updating meter number and currency
- 12 sensor entities per meter:
  - Core: meter reading, meter number, last entry date, consumption delta, days between readings
  - Projection: daily average, monthly projection, yearly projection
  - Cost: current price, last period cost, monthly projected cost, yearly projected cost
- Energy Dashboard compatibility (state_class: total_increasing, device_class: gas/water)
- Service `record_reading` for recording meter readings with optional photo
- Service `set_price` for setting consumption prices with historical tracking
- Service `read_meter_image` for OCR extraction without recording
- Automatic EXIF datetime extraction from photos (used as entry timestamp when no explicit timestamp is provided)
- Graceful degradation when Tesseract is not available
- Persistent storage via HA Store helper (readings, prices, image references)
- Multi-meter support (multiple gas and water meters)
- Visual distinction between gas and water meters (icons, device class)
- English and German translations
- GitHub Actions CI (lint + test)
- SSH deploy key support for private repository access

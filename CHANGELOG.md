# Changelog

All notable changes to the Gas & Water Meter project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-03

### Fixed

- **Fixed invalid statistic_id for Energy Dashboard** — statistic_id now uses lowercase entry_id (e.g., `gas_water_meter:01kgzvqq0qbfexcefmmn82wd4t`). Home Assistant requires lowercase in statistic identifiers. Old invalid statistics are automatically cleaned up on upgrade.
- **Automatic migration of reading statistics** — old erroneous statistics with uppercase entry_id are deleted during the first sync after upgrade

## [0.1.9] - 2026-02-12

### Added

- **New gas meter sensor `price_per_m3`** — converts price from ct/kWh to EUR/m³ using calorific value (Brennwert) and condition factor (Zustandszahl); calculated as: `(price / 100) × calorific_value × condition_factor`
- Energy consumption sensor for Energy Dashboard compatibility (`energy_consumption_total` with `TOTAL_INCREASING` state class)
- German translation for `price_per_m3` sensor ("Preis pro m³")

### Changed

- Gas meters now create 15 sensors (was 14, added energy_consumption_total and price_per_m3)
- Test assertion updated: `test_gas_sensors_created` now expects 15 sensors

## [0.1.8] - 2026-02-11

### Added

- new Gas sensor for faster energy dashboard updates

## [0.1.7] - 2026-02-09

### Added

- **Annual base fee (Jahresgrundgebühr)** — optional per-price base fee that is pro-rated and added to all cost calculations: `last_period_cost` (prorated by days), `monthly_projected_cost` (prorated for one month), `yearly_projected_cost` (full fee); stored in the `prices` table as `base_fee REAL`
- **Gas conversion factors per price entry** — calorific value (Brennwert) and condition factor (Zustandszahl) are now stored per price entry instead of globally, so historical cost calculations use the factors valid at that time; config-entry defaults serve as fallback for legacy data
- **New sensor `current_base_fee`** — shows the annual base fee from the currently active price entry (MONETARY, DIAGNOSTIC)
- Base fee input in sidebar panel price form and edit dialog (for all meter types)
- Base fee column in price history table
- `base_fee` parameter in `set_price` service and WebSocket `add_price`/`update_price` commands

### Changed

- DB schema version 2 → 3 (automatic migration adds `base_fee` column to `prices` table)
- Gas meters now create 14 sensors (was 13); water meters create 13 sensors (was 12)
- Cost calculations use conversion factors from the period-specific price entry (not just the current price)
- Python test count increased from ~227 to 246

## [0.1.6] - 2026-02-09

### Added

- Tesseract training data for getting better result on ocr for gas and water meters (see tessdata/README.md)

## [0.1.5] - 2026-02-09

### Fixed

- Author

## [0.1.3] - 2026-02-09

### Fixed

- **Energy Dashboard compatibility restored** - re-added `state_class=TOTAL_INCREASING` to reading sensor; removing it in 0.1.2 broke Energy Dashboard (sensors could no longer be added, "Statistiken nicht definiert" / "Unerwartete Zustandsklasse" warnings)
- Sensor entity works directly in Energy Dashboard again; external statistics (`gas_water_meter:<entry_id>`) remain available as alternative for correct historical date attribution

## [0.1.2] - 2026-02-09

### Added

- **Tesseract auto-installation** - automatically installs `tesseract-ocr` and language packs (`eng`, `deu`) on first startup via `apk` (Alpine/HAOS) or `apt-get` (Debian/Ubuntu)
- **OCR feedback in UI** - upload response includes `ocr_available` flag; frontend shows success/warning hints after photo upload (Tesseract unavailable, no reading found, successful pre-fill)
- **EXIF timezone support** - correctly extracts `OffsetTimeOriginal`, `OffsetTimeDigitized`, and `OffsetTime` EXIF tags; appends timezone offset to ISO datetime string
- **External statistics for Energy Dashboard** - coordinator imports all readings as external statistics (`gas_water_meter:<entry_id>`) with the reading's actual timestamp, enabling correct historical consumption charts

### Fixed

- **External statistics for historical accuracy** - coordinator imports external statistics (`gas_water_meter:<entry_id>`) with reading timestamps alongside the sensor's recorder statistics; users can optionally use the external statistic in the Energy Dashboard for correct historical date attribution
- **EXIF timestamps 1 hour too early** - timezone offsets from EXIF data were not being extracted, causing naive UTC interpretation; now correctly parsed and appended
- **`ha-icon` not rendering in Companion App** - switched from Lit property bindings (`.icon=`) to HTML attribute bindings (`icon=`) for reliable rendering in custom panels
- **Sidebar menu inaccessible in Companion App** - hamburger menu button is now always displayed, removing the unreliable `narrow` property check
- **Ruff lint violations** - fixed N806, RUF003, RUF001, S607, TRY300, I001, UP017, B905, PLC0415, RUF100, F401 across backend codebase

### Changed

- Reading sensor retains `state_class=TOTAL_INCREASING` for Energy Dashboard compatibility; external statistics with correct timestamps available as alternative
- `ocr.py` refactored: `_check_tesseract()`, `_install_tesseract()`, `ensure_tesseract()` for auto-install workflow
- `__init__.py` calls `ensure_tesseract()` during `async_setup` (runs once via `hass.async_add_executor_job`)
- Python test count increased from ~120 to 227; frontend test count increased from 27 to 72

## [0.1.1] - 2026-02-09

### Added

- **Frontend test infrastructure** — browser-based component tests using Web Test Runner + @open-wc/testing (27 tests covering responsive layout, sidebar toggle, file upload, i18n, navigation)
- **Hamburger menu button** — mobile sidebar navigation via `hass-toggle-menu` event (shown when `narrow=true`)
- **Card-based mobile history** — on narrow screens, the history table is replaced by a card layout with clearly labeled action buttons (min 44px touch targets)
- **Photo upload for existing readings** — upload or replace photos for any reading directly from the history table/cards
- **Scrollable data tables** — horizontal scroll wrappers (`overflow-x: auto`) for tables on small screens
- **New translations** — `upload_photo`, `replace_photo`, `view_photo` in English and German

### Fixed

- **Tab labels hidden on iPhone** — CSS media query at `<600px` was setting `display: none` on tab label text; replaced with vertical icon+label layout
- **File input forced camera-only on iOS** — removed `capture="environment"` attribute so iOS Safari offers camera, photo library, and files selection
- **Icon rendering in tables** — changed `ha-icon` from attribute bindings (`icon="..."`) to property bindings (`.icon=${...}`) for consistent rendering

### Changed

- Backend `ws_update_reading` WebSocket command now accepts optional `image_path` parameter
- Frontend test job added to GitHub Actions CI pipeline (Node.js 20, headless Chrome)

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

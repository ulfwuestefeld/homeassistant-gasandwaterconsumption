# Changelog

All notable changes to the Gas & Water Meter add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-03

### Fixed

- **Fixed invalid statistic_id for Energy Dashboard** — entry_id is now converted to lowercase in statistic identifiers. Home Assistant requires lowercase identifiers, which fixes the `HomeAssistantError: Invalid statistic_id` error
- **Automatic cleanup of old statistics** — erroneous statistics with uppercase entry_id are automatically removed during the first sync after upgrade

## [0.1.9] - 2026-02-12

### Added

- **New sensor `price_per_m3`** for gas meters — converts price from ct/kWh to EUR/m³; uses calorific value (Brennwert) and condition factor (Zustandszahl)
- **Energy consumption total sensor** (`energy_consumption_total`) for Energy Dashboard compatibility with `TOTAL_INCREASING` state class
- German translation: "Preis pro m³"

### Changed

- Gas meters now have 15 sensors (added energy_consumption_total and price_per_m3)
- Updated test: `test_gas_sensors_created` expects 15 sensors

## [0.1.8] - 2026-02-11

### Added

- new Gas sensor for faster energy dashboard updates

## [0.1.7] - 2026-02-09

### Added

- Annual base fee (Jahresgrundgebühr) per price entry — pro-rated into all cost projections
- Gas conversion factors (Brennwert, Zustandszahl) stored per price entry for period-accurate cost calculations
- New sensor: current_base_fee (annual base fee from active price, MONETARY/DIAGNOSTIC)
- base_fee input in sidebar panel price form, edit dialog, and price history table
- base_fee parameter in set_price service and WebSocket add_price/update_price

### Changed

- DB schema version 2 → 3 (adds base_fee column to prices table)
- Gas meters create 14 sensors (was 13); water meters create 13 (was 12)
- Cost calculations use conversion factors from the period-specific price entry

## [0.1.6] - 2026-02-09

### Added

- Tesseract training data for getting better result on ocr for gas and water meters (see tessdata/README.md)

### Fixed

- lazy sensor submission

## [0.1.5] - 2026-02-09

### Fixed

- Author

## [0.1.3] - 2026-02-09

### Fixed

- Energy Dashboard compatibility restored (re-added state_class=TOTAL_INCREASING to reading sensor)
- External statistics remain available as alternative for correct historical date attribution

## [0.1.2] - 2026-02-09

### Added

- Tesseract auto-installation on first startup (apk for Alpine/HAOS, apt-get for Debian/Ubuntu)
- OCR feedback in upload response (ocr_available flag, success/warning hints in UI)
- EXIF timezone offset extraction (OffsetTimeOriginal, OffsetTimeDigitized, OffsetTime)
- External statistics import with correct reading timestamps for Energy Dashboard

### Fixed

- External statistics with correct reading timestamps for accurate historical charts in Energy Dashboard
- EXIF timestamps 1 hour too early (timezone offsets now correctly parsed)
- ha-icon not rendering in Companion App (switched to attribute bindings)
- Sidebar menu inaccessible in Companion App (hamburger button always visible)
- Multiple Ruff lint violations across codebase

### Changed

- Reading sensor retains state_class=TOTAL_INCREASING; external statistics available as alternative for accurate historical attribution
- ocr.py refactored with auto-install workflow (ensure_tesseract)
- async_setup calls ensure_tesseract on first load

## [0.1.1] - 2026-02-09

### Added

- Hamburger menu button for mobile sidebar navigation (fires hass-toggle-menu event)
- Card-based mobile history layout with labeled action buttons (min 44px touch targets)
- Photo upload/replace for existing readings from history table/cards
- Scrollable table wrappers for data tables on narrow screens
- Frontend component tests (Web Test Runner + @open-wc/testing, 27 tests)

### Fixed

- Tab labels hidden on iPhone (CSS media query replaced display:none with vertical layout)
- File input forced camera-only on iOS (removed capture="environment" attribute)
- Icon property bindings in history/prices tables for consistent rendering

### Changed

- Backend ws_update_reading now accepts optional image_path parameter
- Frontend test job added to CI pipeline

## [0.1.0] - 2026-02-08

### Added

- Meter number change detection: consumption resets on meter replacement; projections use only current meter
- Gas energy conversion: calorific value (Brennwert, kWh/m³) and condition factor (Zustandszahl)
- Energy consumption sensor for gas meters (kWh)
- Gas-specific pricing in ct/kWh (cost = kWh × ct/kWh / 100)
- Two-step config flow for gas meters (base + conversion factors)
- WebSocket command `update_gas_params` for updating conversion factors from frontend
- Gas conversion factor editing in sidebar panel (Prices tab)
- Mobile responsive history with card layout and touch-friendly buttons
- Photo upload/replace for existing readings from history table
- Scrollable table wrappers for narrow screens
- Monthly consumption chart: consumption aggregated by calendar month with proportional distribution

### Changed

- Gas meters now create 13 sensors (12 common + energy_consumption); water meters still create 12
- Gas price sensor shows ct/kWh instead of EUR/m³
- Frontend price form adapts labels and units based on meter type
- Options flow includes gas conversion factors for gas meters
- Projections and consumption statistics respect meter number boundaries

## [0.0.4] - 2026-02-08

### Added

- Graphical user interface (GUI) accessible via Home Assistant sidebar
- SQLite database backend (replaces JSON file storage)
- WebSocket API for frontend-backend communication
- REST API endpoint for image uploads
- Consumption chart visualization (Chart.js)
- Price validity periods (valid_from / valid_to)
- Photo upload with client-side validation (max 20 MB, max 21 MP)
- Automatic migration from legacy JSON store to SQLite
- HEIC/HEIF photo support via pillow-heif (pre-installed in add-on)

### Changed

- Storage migrated from HA JSON Store to SQLite via aiosqlite
- Sensor entity category and device class fixes for HA 2025.1+ compliance
- Sidebar title changed to English for international accessibility
- Frontend panel fully internationalized (English/German) via hass.language

### Fixed

- Service handlers not being awaited (lambda wrapping issue)
- Sensor validation errors for current_price and daily_average
- Windows test compatibility with pytest-socket

## [0.0.3] - 2026-02-08

### Fixed

- Fixed add-on installation failure: removed `image` field from `config.yaml` (no pre-built image on ghcr.io)
- Fixed CRLF line endings in `run.sh` causing Docker execution failure on Linux
- Added `dos2unix` to Dockerfile to convert line endings at build time
- Fixed architecture mismatch between `config.yaml` and `build.yaml`

## [0.0.2] - 2026-02-08

### Fixed

- Fixed missing `__init__.py` in `custom_components/` package
- Fixed coordinator compatibility with newer HA versions
- Set codeowner to `ulfwuestefeld`

## [0.0.1] - 2026-02-08

### Added

- Initial release as Home Assistant add-on
- Automatic installation of custom integration to Home Assistant config
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
- Graceful degradation when Tesseract is not available in HA core
- Persistent storage via HA Store helper (readings, prices, image references)
- Multi-meter support (multiple gas and water meters)
- Visual distinction between gas and water meters (icons, device class)
- English and German translations

# Changelog

All notable changes to the Gas & Water Meter add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

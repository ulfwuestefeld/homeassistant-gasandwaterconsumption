# Changelog

All notable changes to the Gas & Water Meter integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-02-08

### Added

- Initial release
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
- Tesseract OCR support for extracting meter readings from photos
- Image preprocessing pipeline (grayscale, contrast, threshold)
- Graceful degradation when Tesseract is not installed
- Persistent storage via HA Store helper (readings, prices, image references)
- Multi-meter support (multiple gas and water meters)
- Visual distinction between gas and water meters (icons, device class)
- English and German translations
- Unit tests for config flow, sensors, storage, services, coordinator, and OCR

# Free and Open Source Software (FOSS) Dependencies

This document lists all third-party open source components used by the Gas & Water Meter integration.

## Runtime Dependencies

| Component | Version | License | URL |
|-----------|---------|---------|-----|
| pytesseract | >= 0.3.10 | Apache-2.0 | https://github.com/madmaze/pytesseract |
| tesseract-ocr (system) | >= 4.0 | Apache-2.0 | https://github.com/tesseract-ocr/tesseract |

## Home Assistant Core Dependencies (always available)

| Component | License | Usage |
|-----------|---------|-------|
| voluptuous | BSD-3-Clause | Schema validation in config flow and services |
| Pillow | HPND | Image preprocessing for OCR |
| orjson | MIT / Apache-2.0 | JSON serialization (via HA storage) |
| aiohttp | Apache-2.0 | Async HTTP (via HA core) |

## Test Dependencies

| Component | Version | License | URL |
|-----------|---------|---------|-----|
| pytest | >= 8.0.0 | MIT | https://github.com/pytest-dev/pytest |
| pytest-asyncio | >= 0.23.0 | Apache-2.0 | https://github.com/pytest-dev/pytest-asyncio |
| pytest-homeassistant-custom-component | >= 0.13.0 | MIT | https://github.com/MatthewFlamworthy/pytest-homeassistant-custom-component |

## License Compatibility

All listed dependencies use licenses compatible with the MIT license of this project:
- Apache-2.0: Compatible with MIT
- BSD-3-Clause: Compatible with MIT
- HPND (Historical Permission Notice and Disclaimer): Compatible with MIT

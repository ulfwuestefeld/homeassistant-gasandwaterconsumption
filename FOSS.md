# Free and Open Source Software (FOSS) Dependencies

This document lists all third-party open source components used by the Gas & Water Meter add-on and integration.

## Runtime Dependencies (Python)

| Component | Version | License | URL |
|-----------|---------|---------|-----|
| pytesseract | >= 0.3.10 | Apache-2.0 | https://github.com/madmaze/pytesseract |
| aiosqlite | >= 0.20.0 | MIT | https://github.com/omnilib/aiosqlite |
| pillow-heif | >= 0.18.0 | BSD-3-Clause | https://github.com/bigcat88/pillow_heif |
| tesseract-ocr (system) | >= 4.0 | Apache-2.0 | https://github.com/tesseract-ocr/tesseract |

## Runtime Dependencies (Frontend, bundled)

| Component | Version | License | URL |
|-----------|---------|---------|-----|
| lit | ^3.2.0 | BSD-3-Clause | https://github.com/lit/lit |
| chart.js | ^4.4.0 | MIT | https://github.com/chartjs/Chart.js |

## Add-on Container Dependencies

| Component | License | Usage |
|-----------|---------|-------|
| Alpine Linux | MIT | Add-on base image (via HA base image) |
| libheif | LGPL-3.0 | HEIC/HEIF image decoding (system library, dynamically linked) |
| bashio | Apache-2.0 | Add-on shell scripting helper |

## Home Assistant Core Dependencies (always available)

| Component | License | Usage |
|-----------|---------|-------|
| voluptuous | BSD-3-Clause | Schema validation in config flow and services |
| Pillow | HPND | Image preprocessing for OCR, EXIF extraction |
| aiohttp | Apache-2.0 | REST API for image uploads (via HA core) |

## Test Dependencies

| Component | Version | License | URL |
|-----------|---------|---------|-----|
| pytest | >= 8.0.0 | MIT | https://github.com/pytest-dev/pytest |
| pytest-asyncio | >= 0.23.0 | Apache-2.0 | https://github.com/pytest-dev/pytest-asyncio |
| pytest-homeassistant-custom-component | >= 0.13.0 | MIT | https://github.com/MatthewFlamworthy/pytest-homeassistant-custom-component |
| pytest-cov | >= 6.0.0 | MIT | https://github.com/pytest-dev/pytest-cov |
| pytest-timeout | >= 2.3.0 | MIT | https://github.com/pytest-dev/pytest-timeout |
| ruff | >= 0.9.0 | MIT | https://github.com/astral-sh/ruff |

## License Compatibility

All listed dependencies use licenses compatible with the MIT license of this project:
- MIT: Same license
- Apache-2.0: Compatible with MIT
- BSD-3-Clause: Compatible with MIT
- LGPL-3.0: Compatible with MIT (dynamically linked)
- HPND (Historical Permission Notice and Disclaimer): Compatible with MIT

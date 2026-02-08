# Software Bill of Materials (SBOM)

## Gas & Water Meter Add-on v0.1.0

### Metadata

- **Name**: Gas & Water Meter
- **Domain**: gas_water_meter
- **Version**: 0.1.0
- **Type**: Home Assistant Add-on + Custom Integration
- **Python**: >= 3.12
- **Home Assistant**: >= 2024.1.0

### Add-on Container Components

| Package | Type | License |
|---------|------|---------|
| Alpine Linux (HA base image) | OS | MIT |
| tesseract-ocr | System binary (pre-installed) | Apache-2.0 |
| bashio | Shell library | Apache-2.0 |

### Direct Python Dependencies

| Package | Version Constraint | Type | License |
|---------|--------------------|------|---------|
| pytesseract | >= 0.3.10 | Runtime (optional) | Apache-2.0 |
| aiosqlite | >= 0.20.0 | Runtime (required) | MIT |
| pillow-heif | >= 0.18.0 | Runtime (required) | BSD-3-Clause |
| tesseract-ocr | >= 4.0 | System binary (optional) | Apache-2.0 |
| libheif | (system) | System library (required) | LGPL-3.0 |

### Direct Frontend Dependencies

| Package | Version Constraint | Type | License |
|---------|--------------------|------|---------|
| lit | ^3.2.0 | Runtime (bundled) | BSD-3-Clause |
| chart.js | ^4.4.0 | Runtime (bundled) | MIT |

### HA Core Built-in Dependencies Used

| Package | Usage |
|---------|-------|
| voluptuous | Config flow & service schema validation |
| Pillow | Image preprocessing for OCR, EXIF extraction |
| aiohttp | REST API for image uploads |
| homeassistant.helpers.update_coordinator | Data coordination |

### Test Dependencies

| Package | Version Constraint | License |
|---------|--------------------|---------|
| pytest | >= 8.0.0 | MIT |
| pytest-asyncio | >= 0.23.0 | Apache-2.0 |
| pytest-homeassistant-custom-component | >= 0.13.0 | MIT |
| pytest-cov | >= 6.0.0 | MIT |
| pytest-timeout | >= 2.3.0 | MIT |
| ruff | >= 0.9.0 | MIT |

### Frontend Build Dependencies

| Package | Version Constraint | License |
|---------|--------------------|---------|
| rollup | ^4.0.0 | MIT |
| @rollup/plugin-node-resolve | ^16.0.0 | MIT |
| @rollup/plugin-terser | ^0.4.0 | MIT |

### Transitive Dependencies

pytesseract depends on:
- Pillow (already in HA core)

pillow-heif depends on:
- libheif (system library, dynamically linked via LGPL-3.0)
- Pillow (already in HA core)

lit depends on:
- @lit/reactive-element, lit-element, lit-html (all BSD-3-Clause, bundled)

No additional transitive runtime dependencies beyond those bundled are introduced.

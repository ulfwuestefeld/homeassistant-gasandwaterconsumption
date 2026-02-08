# Software Bill of Materials (SBOM)

## Gas & Water Meter Integration v0.0.1

### Integration Metadata

- **Name**: Gas & Water Meter
- **Domain**: gas_water_meter
- **Version**: 0.0.1
- **Python**: >= 3.12
- **Home Assistant**: >= 2024.1.0

### Direct Dependencies

| Package | Version Constraint | Type | License |
|---------|--------------------|------|---------|
| pytesseract | >= 0.3.10 | Runtime (optional) | Apache-2.0 |
| tesseract-ocr | >= 4.0 | System binary (optional) | Apache-2.0 |

### HA Core Built-in Dependencies Used

| Package | Usage |
|---------|-------|
| voluptuous | Config flow & service schema validation |
| Pillow | Image preprocessing for OCR |
| homeassistant.helpers.storage | Persistent data storage |
| homeassistant.helpers.update_coordinator | Data coordination |

### Test Dependencies

| Package | Version Constraint | License |
|---------|--------------------|---------|
| pytest | >= 8.0.0 | MIT |
| pytest-asyncio | >= 0.23.0 | Apache-2.0 |
| pytest-homeassistant-custom-component | >= 0.13.0 | MIT |

### Transitive Dependencies

pytesseract depends on:
- Pillow (already in HA core)

No additional transitive runtime dependencies are introduced.

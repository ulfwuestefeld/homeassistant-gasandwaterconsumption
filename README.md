# Gas & Water Meter - Home Assistant Add-on

A Home Assistant add-on that provides a custom integration for manually recording gas and water meter readings with optional photo capture and OCR, consumption projection, and cost tracking.

## Features

- **Manual meter reading entry** via Home Assistant services
- **Multiple meters** — add as many gas and/or water meters as needed
- **Energy Dashboard compatible** — sensors use `state_class: total_increasing` with proper device classes
- **Photo capture** — attach photos to meter readings for documentation
- **Tesseract OCR** — extract meter readings and serial numbers from photos (pre-installed in add-on)
- **EXIF date extraction** — when uploading a photo without a timestamp, the capture date from the photo's EXIF data is used automatically
- **Consumption projection** — daily average, monthly, and yearly projections based on historical data
- **Price tracking** — record current and historical prices for cost calculations
- **Cost sensors** — last period cost, monthly and yearly projected costs
- **Full i18n** — English and German translations

## Sensors (per meter)

| Sensor | Description |
|--------|-------------|
| Meter reading | Current meter reading (m³) — Energy Dashboard |
| Meter number | Physical meter serial number |
| Last entry date | When the last reading was recorded |
| Last consumption | Delta between last two readings (m³) |
| Days between readings | Days between last two readings |
| Daily average consumption | Average daily consumption (m³/day) |
| Monthly projection | Projected monthly consumption (m³) |
| Yearly projection | Projected yearly consumption (m³) |
| Current price | Active price per m³ |
| Last period cost | Cost for the last consumption period |
| Monthly projected cost | Projected monthly cost |
| Yearly projected cost | Projected yearly cost |

## Installation

### Prerequisites

This is a **private repository**. To use it as an add-on repository in Home Assistant, you need an SSH deploy key configured:

1. Add the deploy key's **private key** to your Home Assistant instance at `/ssl/` or via the SSH add-on
2. Configure SSH in Home Assistant to use the deploy key for `github.com`

### Adding the Add-on Repository

1. In Home Assistant, go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the **⋮** menu (top right) → **Repositories**
3. Add the repository URL: `ssh://git@github.com/ulfwuestefeld/gasandwater.git`
4. Click **Add** → **Close**
5. Find **Gas & Water Meter** in the add-on store and click **Install**

### Activating the Integration

1. **Start** the Gas & Water Meter add-on
2. Check the add-on logs — it will confirm the integration files were installed
3. **Restart Home Assistant** (Settings → System → Restart)
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for "Gas & Water Meter"

## Configuration

After restarting Home Assistant:

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "Gas & Water Meter"
3. Select meter type (Gas or Water)
4. Enter a name, meter number, and currency
5. Repeat for additional meters

## Usage

### Recording a Meter Reading

Call the `gas_water_meter.record_reading` service:

```yaml
service: gas_water_meter.record_reading
data:
  config_entry_id: "<your_entry_id>"
  meter_reading: 1234.567
  timestamp: "2026-02-08T10:30:00"
```

With a photo (OCR extraction):

```yaml
service: gas_water_meter.record_reading
data:
  config_entry_id: "<your_entry_id>"
  image: "/media/meter_photos/gas_meter.jpg"
```

### Setting a Price

```yaml
service: gas_water_meter.set_price
data:
  config_entry_id: "<your_entry_id>"
  price_per_unit: 1.85
  valid_from: "2026-01-01"
```

### Reading a Meter Image (OCR only)

```yaml
service: gas_water_meter.read_meter_image
data:
  image: "/media/meter_photos/gas_meter.jpg"
```

Returns the extracted meter reading, meter number, confidence score, and raw OCR text.

## Energy Dashboard

The **Meter reading** sensor is compatible with the Home Assistant Energy Dashboard:

1. Go to **Settings** > **Dashboards** > **Energy**
2. Add the gas meter sensor under **Gas consumption**
3. Add the water meter sensor under **Water consumption**

## Updating

When a new version is available:

1. Update the add-on in the Add-on Store
2. Start or restart the add-on (updated integration files are copied automatically)
3. Restart Home Assistant to apply the changes

## Repository Structure

```
├── repository.yaml              # Add-on repository metadata
├── gas-water-meter/             # The add-on
│   ├── config.yaml              # Add-on configuration
│   ├── Dockerfile               # Container build (includes Tesseract)
│   ├── build.yaml               # Multi-architecture build config
│   ├── run.sh                   # Startup script (copies integration files)
│   ├── DOCS.md                  # Add-on documentation
│   ├── CHANGELOG.md             # Add-on changelog
│   ├── icon.png / logo.png      # Add-on branding
│   ├── translations/            # Add-on translations
│   └── custom_components/       # The HA custom integration
│       └── gas_water_meter/
├── tests/                       # Unit tests
├── .github/workflows/           # CI (lint + test)
├── pyproject.toml               # Python project config
└── requirements_test.txt        # Test dependencies
```

## Development

### Running Tests

```bash
pip install -r requirements_test.txt
pytest tests/ -v
```

### Linting

```bash
ruff check gas-water-meter/custom_components/ tests/
ruff format --check gas-water-meter/custom_components/ tests/
```

## License

MIT License. See [FOSS.md](FOSS.md) for third-party licenses.

## Version

0.0.3 — See [CHANGELOG.md](CHANGELOG.md) for details.

# Gas & Water Meter - Home Assistant Add-on

A Home Assistant add-on that provides a custom integration for manually recording gas and water meter readings with optional photo capture and OCR, consumption projection, and cost tracking.

## Features

- **Graphical user interface** — sidebar panel for managing meters, readings, prices, and photo uploads directly in the browser
- **Mobile responsive** — card-based layout on narrow screens with touch-friendly action buttons
- **Manual meter reading entry** — via GUI panel or Home Assistant services
- **Multiple meters** — add as many gas and/or water meters as needed
- **Meter replacement support** — when the meter number changes between readings, consumption resets automatically; projections are based only on the current meter
- **Energy Dashboard compatible** — sensors use `state_class: total_increasing` with proper device classes; additionally, external statistics with correct reading timestamps are imported (statistic ID: `gas_water_meter:<entry_id>`)
- **Photo capture & upload** — attach photos in JPEG, PNG, HEIC/HEIF format (max 20 MB, 21 megapixels) with client-side validation; upload photos for existing readings from the history table
- **Tesseract OCR** — extract meter readings and serial numbers from photos (pre-installed in add-on)
- **HEIC/HEIF support** — Apple photo format supported via pillow-heif (pre-installed in add-on)
- **EXIF date extraction** — when uploading a photo without a timestamp, the capture date from the photo's EXIF data is used automatically
- **Monthly consumption chart** — Chart.js visualization always aggregated by calendar month; reading periods spanning multiple months are distributed proportionally
- **Gas energy conversion** — configure calorific value (Brennwert) and condition factor (Zustandszahl) to convert m³ to kWh
- **Consumption projection** — daily average, monthly, and yearly projections based on historical data
- **Price tracking** — gas: ct/kWh, water: EUR/m³ with validity periods (valid_from / valid_to)
- **Annual base fee** — optional per-price base fee (Jahresgrundgebühr) that is pro-rated and included in all cost projections
- **Gas conversion factors per price** — calorific value and condition factor stored per price entry for period-accurate cost calculations
- **Cost sensors** — costs computed from energy consumption (gas: kWh × ct/kWh) or volume (water: m³ × EUR/m³), including pro-rated annual base fee
- **SQLite storage** — persistent data storage using SQLite via aiosqlite
- **Full i18n** — English and German translations

## Sensors (per meter)

| Sensor | Description | Gas | Water |
|--------|-------------|-----|-------|
| Meter reading | Current meter reading (m³) — Energy Dashboard | x | x |
| Meter number | Physical meter serial number | x | x |
| Last entry date | When the last reading was recorded | x | x |
| Last consumption | Delta between last two readings (m³) | x | x |
| Energy consumption | Last period in kWh (m³ × Brennwert × Zustandszahl) | x | - |
| Days between readings | Days between last two readings | x | x |
| Daily average consumption | Average daily consumption (m³/day) | x | x |
| Monthly projection | Projected monthly consumption (m³) | x | x |
| Yearly projection | Projected yearly consumption (m³) | x | x |
| Current price | Active price (gas: ct/kWh, water: EUR/m³) | x | x |
| Annual base fee | Annual base fee from active price entry | x | x |
| Last period cost | Cost for the last consumption period (incl. pro-rated base fee) | x | x |
| Monthly projected cost | Projected monthly cost (incl. pro-rated base fee) | x | x |
| Yearly projected cost | Projected yearly cost (incl. annual base fee) | x | x |

## Installation

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
5. For gas meters: enter calorific value (Brennwert) and condition factor (Zustandszahl) from your gas bill
6. Repeat for additional meters

## Usage

### Sidebar Panel (GUI)

After installation, a **Gas & Water Meter** entry appears in the Home Assistant sidebar. The panel provides:

- **Meter selection** — switch between configured meters via tabs
- **Reading entry** — enter meter readings manually or upload a photo for OCR
- **History table** — view, edit, and delete past readings with consumption data
- **Price management** — set prices with validity periods (valid_from / valid_to)
- **Monthly consumption chart** — visualize consumption per calendar month

### Recording a Meter Reading (Service)

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

For gas (ct/kWh) with conversion factors and base fee:
```yaml
service: gas_water_meter.set_price
data:
  config_entry_id: "<your_entry_id>"
  price_per_unit: 8.45
  valid_from: "2026-01-01"
  calorific_value: 11.2        # optional: Brennwert (kWh/m³)
  condition_factor: 0.9524     # optional: Zustandszahl
  base_fee: 120.00             # optional: Jahresgrundgebühr (EUR/year)
```

For water (EUR/m³) with base fee:
```yaml
service: gas_water_meter.set_price
data:
  config_entry_id: "<your_entry_id>"
  price_per_unit: 1.85
  valid_from: "2026-01-01"
  base_fee: 60.00              # optional: Jahresgrundgebühr (EUR/year)
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

> **Tip for correct historical dates:** The sensor entity attributes consumption to the moment you enter a reading. For correct historical attribution (consumption shown at the actual reading date), use the external statistic `gas_water_meter:<your_entry_id>` instead of the sensor entity. This external statistic is automatically imported by the integration with the reading's actual timestamp.

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
│           ├── __init__.py      # Entry setup, services, panel registration
│           ├── config_flow.py   # UI config flow + options flow
│           ├── const.py         # Constants, icon mappings
│           ├── coordinator.py   # Data coordinator (projection + cost)
│           ├── db.py            # SQLite database layer (aiosqlite)
│           ├── http.py          # REST API for image uploads
│           ├── websocket.py     # WebSocket API for frontend
│           ├── ocr.py           # Tesseract OCR wrapper + EXIF + HEIC/HEIF
│           ├── sensor.py        # 14 sensor entities (gas) / 13 (water)
│           ├── store.py         # Legacy JSON storage (migration only)
│           └── frontend/        # Bundled panel JS (Lit + Chart.js)
├── frontend-src/                # Frontend source (Lit, Chart.js, Rollup)
├── tests/                       # Python unit tests (~246 tests)
├── .github/workflows/           # CI (lint + test)
├── pyproject.toml               # Python project config
└── requirements_test.txt        # Test dependencies
```

## Development

### Running Python Tests

```bash
pip install -r requirements_test.txt
pytest tests/ -v
```

### Running Frontend Tests

```bash
cd frontend-src
npm ci
npm test
```

### Linting

```bash
ruff check gas-water-meter/custom_components/ tests/
ruff format --check gas-water-meter/custom_components/ tests/
```

### Building the Frontend

```bash
cd frontend-src
npm run build
```

## License

MIT License. See [FOSS.md](FOSS.md) for third-party licenses.

## Version

0.1.7 — See [CHANGELOG.md](CHANGELOG.md) for details.

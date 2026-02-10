# Gas & Water Meter

A Home Assistant add-on that installs a custom integration for manually recording gas and water meter readings with optional photo capture and OCR, consumption projection, and cost tracking.

## How it works

This add-on installs the **Gas & Water Meter** custom integration into your Home Assistant instance. On startup, it copies the integration files to your `/config/custom_components/` directory. After installation, restart Home Assistant to activate the integration.

## Features

- **Graphical user interface** — sidebar panel for managing meters, readings, prices, and photo uploads directly in the browser
- **Mobile responsive** — card-based layout on narrow screens with touch-friendly buttons
- **Manual meter reading entry** — via GUI panel or Home Assistant services
- **Multiple meters** — add as many gas and/or water meters as needed
- **Meter replacement support** — when the meter number changes, consumption resets automatically; projections are based only on the current meter
- **Energy Dashboard compatible** — sensors use `state_class: total_increasing` with proper device classes
- **Photo capture & upload** — attach photos in JPEG, PNG, HEIC/HEIF format (max 20 MB, 21 megapixels) with automatic OCR; upload photos for existing readings from the history table
- **HEIC/HEIF support** — Apple photo format supported via pillow-heif (pre-installed in add-on)
- **Tesseract OCR** — extract meter readings and serial numbers from photos (Tesseract is pre-installed in this add-on)
- **EXIF date extraction** — when uploading a photo without a timestamp, the capture date from the photo's EXIF data is used automatically
- **Monthly consumption chart** — consumption always aggregated by calendar month; reading periods spanning multiple months are distributed proportionally
- **Gas energy conversion** — configure calorific value (Brennwert) and condition factor (Zustandszahl) to convert m³ to kWh
- **Consumption projection** — daily average, monthly, and yearly projections based on historical data
- **Price tracking** — gas: ct/kWh, water: EUR/m³ with validity periods (valid_from / valid_to)
- **Annual base fee** — optional per-price base fee (Jahresgrundgebühr) that is pro-rated and included in all cost projections
- **Gas conversion factors per price** — calorific value and condition factor stored per price entry for period-accurate cost calculations
- **Cost sensors** — costs computed from energy consumption (gas: kWh × ct/kWh) or volume (water: m³ × EUR/m³), including pro-rated annual base fee
- **SQLite storage** — persistent data storage using SQLite (automatic migration from earlier versions)
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

1. Install this add-on from the add-on store
2. Start the add-on — it will copy the integration files automatically
3. **Restart Home Assistant** to activate the integration
4. Go to **Settings** → **Devices & Services** → **Add Integration** and search for "Gas & Water Meter"

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

After installation and restart, a **Gas & Water Meter** entry appears in the Home Assistant sidebar. The panel provides:

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

## Energy Dashboard

The **Meter reading** sensor is compatible with the Home Assistant Energy Dashboard:

1. Go to **Settings** > **Dashboards** > **Energy**
2. Add the gas meter sensor under **Gas consumption**
3. Add the water meter sensor under **Water consumption**

## Updates

When a new version of this add-on is available:

1. Update the add-on in the add-on store
2. Start or restart the add-on (updated files are copied automatically)
3. Restart Home Assistant to apply changes

# Gas & Water Meter

A Home Assistant add-on that installs a custom integration for manually recording gas and water meter readings with optional photo capture and OCR, consumption projection, and cost tracking.

## How it works

This add-on installs the **Gas & Water Meter** custom integration into your Home Assistant instance. On startup, it copies the integration files to your `/config/custom_components/` directory. After installation, restart Home Assistant to activate the integration.

## Features

- **Graphical user interface** — sidebar panel for managing meters, readings, prices, and photo uploads directly in the browser
- **Manual meter reading entry** — via GUI panel or Home Assistant services
- **Multiple meters** — add as many gas and/or water meters as needed
- **Energy Dashboard compatible** — sensors use `state_class: total_increasing` with proper device classes
- **Photo capture & upload** — attach photos in JPEG, PNG, HEIC/HEIF format (max 20 MB, 21 megapixels) with automatic OCR
- **HEIC/HEIF support** — Apple photo format supported via pillow-heif (pre-installed in add-on)
- **Tesseract OCR** — extract meter readings and serial numbers from photos (Tesseract is pre-installed in this add-on)
- **EXIF date extraction** — when uploading a photo without a timestamp, the capture date from the photo's EXIF data is used automatically
- **Consumption chart** — visualization of historical consumption and meter readings
- **Consumption projection** — daily average, monthly, and yearly projections based on historical data
- **Price tracking** — record prices with validity periods (valid_from / valid_to) for cost calculations
- **Cost sensors** — last period cost, monthly and yearly projected costs
- **SQLite storage** — persistent data storage using SQLite (automatic migration from earlier versions)
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
5. Repeat for additional meters

## Usage

### Sidebar Panel (GUI)

After installation and restart, a **Gas & Water Meter** entry appears in the Home Assistant sidebar. The panel provides:

- **Meter selection** — switch between configured meters via tabs
- **Reading entry** — enter meter readings manually or upload a photo for OCR
- **History table** — view, edit, and delete past readings with consumption data
- **Price management** — set prices with validity periods (valid_from / valid_to)
- **Consumption chart** — visualize consumption trends over time

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

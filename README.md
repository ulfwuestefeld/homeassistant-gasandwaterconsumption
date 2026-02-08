# Gas & Water Meter - Home Assistant Custom Integration

A Home Assistant custom integration for manually recording gas and water meter readings with optional photo capture and OCR, consumption projection, and cost tracking.

## Features

- **Manual meter reading entry** via Home Assistant services
- **Multiple meters** -- add as many gas and/or water meters as needed
- **Energy Dashboard compatible** -- sensors use `state_class: total_increasing` with proper device classes
- **Photo capture** -- attach photos to meter readings for documentation
- **Tesseract OCR** -- optionally extract meter readings and serial numbers from photos
- **Consumption projection** -- daily average, monthly, and yearly projections based on historical data
- **Price tracking** -- record current and historical prices for cost calculations
- **Cost sensors** -- last period cost, monthly and yearly projected costs
- **Full i18n** -- English and German translations

## Sensors (per meter)

| Sensor | Description |
|--------|-------------|
| Meter reading | Current meter reading (m³) -- Energy Dashboard |
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

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "Gas & Water Meter" and install
3. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/gas_water_meter` directory to your Home Assistant `custom_components` folder
2. Restart Home Assistant

### Tesseract OCR (Optional)

To use the photo OCR feature, install Tesseract:

**Home Assistant OS (via SSH Add-on):**
```bash
apk add tesseract-ocr
```

**Docker:**
```bash
apt-get install tesseract-ocr
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

## Configuration

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

## License

MIT License. See [FOSS.md](FOSS.md) for third-party licenses.

## Version

0.0.1 -- Initial release. See [CHANGELOG.md](CHANGELOG.md) for details.

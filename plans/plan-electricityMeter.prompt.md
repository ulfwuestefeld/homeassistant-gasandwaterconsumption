# Plan: Elektrizitäts-Meter-Typ implementieren

**TL;DR**: Neuer Meter-Typ "Electricity" als dritter Meter-Typ analog zu Gas & Water. Verbrauch und Einspeisung als **ein Meter mit zwei optionalen Zählerständen**, zwei unabhängige Preislinien (Consumption & Feed-in) mit Historien-Unterstützung, separate Grundgebühren. Schema-Migration v4 (feed_in_reading, direction columns). 13–26 Sensoren je nach Config. Kosten-Berechnung: `kWh × price_ct/kWh ÷ 100 + pro-ratierte Grundgebühr EUR`. Tests: >300 Tests (20-24 neue für Electricity).

---

## Implementation Steps

### 1. **[const.py](const.py) aktualisieren** — Meter-Typ definieren

- `METER_TYPE_ELECTRICITY = "electricity"` konstante hinzufügen
- `METER_TYPES` Liste auf 3 Typen erweitern: `[METER_TYPE_GAS, METER_TYPE_WATER, METER_TYPE_ELECTRICITY]`
- Icon-Mappings für Electricity (mdi:lightning-bolt für Gerät, mdi:transmission-tower-export für Einspeisung)
- Device-Name-Präfixe: "Electricity Meter", "Power Meter", oder "Strom Meter" (DE)
- Keine neuen Konstanten für Spanning/Voltage nötig (einfaches m³ → kWh Modell)

### 2. **[config_flow.py](gas-water-meter/custom_components/gas_water_meter/config_flow.py) erweitern** — Elektrizität im Setup-Flow

- Meter-Type-Auswahl: "Gas" / "Water" / "Electricity" hinzufügen
- **Electricity benötigt KEINE zusätzlichen Parameter wie Gas** (keine Konversionsfaktoren nötig — kWh direkt)
- Single-step config (wie Water): Meter-Name, Meter-Nummer, Währung, Meter-Typ
- **Optional**: Auswahl "Verbrauch", "Einspeisung" oder "Beide" (für Dual-Purpose-Zähler)
- Unique-ID-Schema: `gas_water_meter_electricity_<meter_number>`
- Validierung: Meter-Nummer eindeutig pro Meter-Typ (Gas-12345 und Electricity-12345 beide erlaubt)

### 3. **[sensor.py](gas-water-meter/custom_components/gas_water_meter/sensor.py) — 13–26 neue Sensoren hinzufügen**

**Modell**: Ein Meter kann Verbrauch UND/ODER Einspeisung tracken.
- Wenn nur Verbrauch: 13 Sensoren (gleich wie Water)
- Wenn nur Einspeisung: 13 Sensoren mit Einspeisung-Icons
- Wenn beide: 26 Sensoren (13 Verbrauch + 13 Einspeisung) mit unterschiedlichen Keys/Icons

Basis-Sensoren pro Richtung (13 je Richtung):
- `reading` / `reading_feed_in`: Zählerstand in kWh (TOTAL_INCREASING)
- `meter_number`: Diagnose (gemeinsam)
- `last_entry_date` / `last_entry_date_feed_in`: Zeitstempel
- `consumption` / `feed_in`: Verbrauch/Einspeisung in kWh (Diagnose)
- `days_between` / `days_between_feed_in`: Tage seit letztem Eintrag
- `daily_average` / `daily_average_feed_in`: kWh/d (Grundlage Projektion)
- `monthly_projection` / `monthly_projection_feed_in`: monatliche Hochrechnung kWh
- `yearly_projection` / `yearly_projection_feed_in`: jährliche Hochrechnung kWh
- `current_price` / `current_price_feed_in`: aktueller Tarif in ct/kWh (Diagnose)
- `last_period_cost` / `last_period_cost_feed_in`: Kosten/Erträge letzte Periode in EUR
- `monthly_projected_cost` / `monthly_projected_cost_feed_in`: monatliche Kosten-/Ertrags-Hochrechnung
- `yearly_projected_cost` / `yearly_projected_cost_feed_in`: jährliche Kosten-/Ertrags-Hochrechnung
- `current_base_fee` / `current_base_fee_feed_in`: aktuelle Grundgebühr EUR/Jahr

Device Classes:
- `reading`, `consumption`: `SensorDeviceClass.ENERGY`
- `monthly_projection`, `yearly_projection`: `SensorDeviceClass.ENERGY`
- `current_price`: `SensorDeviceClass.MONETARY`
- Costs/feed_in_revenue: `SensorDeviceClass.MONETARY`

Icon-Anpassungen für Electricity-Sensoren:
- Consumption icons: `mdi:lightning-bolt` (Verbrauch)
- Feed-in icons: `mdi:transmission-tower-export` (Einspeisung)

### 4. **[coordinator.py](gas-water-meter/custom_components/gas_water_meter/coordinator.py) — Berechnungen erweitern**

- `MeterCoordinatorData` — **neue optionale Felder** für Einspeisung:
  - `feed_in_reading: float | None` — Einspeisung Zählerstand
  - `feed_in_consumption: float | None` — Einspeisung Verbrauch (Periode)
  - `feed_in_daily_average: float | None` — kWh/d Einspeisung
  - `feed_in_monthly_projection: float | None` — monatliche Einspeisung Hochrechnung
  - `feed_in_yearly_projection: float | None` — jährliche Einspeisung Hochrechnung
  - `feed_in_last_period_cost: float | None` — Ertrag letzte Periode (als negative Kosten)
  - `feed_in_monthly_projected_cost: float | None` — monatliche Ertragsrechnung
  - `feed_in_yearly_projected_cost: float | None` — jährliche Ertragsrechnung
  - `feed_in_current_price: float | None` — aktueller Einspeisung-Tarif ct/kWh
  - `feed_in_current_base_fee: float | None` — Grundgebühr Einspeisung

- `_compute_cost()` Methode:
  - Electricity: `cost = consumption_kWh × price_ct/kWh ÷ 100 + pro-ratierte_grundgebühr_eur`
  - Feed-in: `revenue = feed_in_kWh × price_ct/kWh ÷ 100 + pro-ratierte_grundgebühr_eur` (als negative Kosten für Ertrag)
  - Existierende Logik: `if meter_type == METER_TYPE_GAS: ... elif meter_type == METER_TYPE_WATER: ... else: # Electricity`

- `_async_update_data()` — **muss zwei Preislinien abfragen**:
  - Verbrauch: `async_get_current_price(meter_number, direction='consumption')`
  - Einspeisung: `async_get_current_price(meter_number, direction='feed_in')`

- Projektions-Berechnungen: Gleich wie Water (einfacher Durchschnitt × Tage im Monat/Jahr)
- **Neue Komplexität**: Dual-Channel-Berechnungen für Verbrauch und Einspeisung parallel

### 5. **[db.py](gas-water-meter/custom_components/gas_water_meter/db.py) — Anpassungen für Dual-Channel-Preise**

- `readings` Tabelle: Neue optionale Spalte `feed_in_reading REAL` (NULL wenn nur Verbrauch)
  - Ermöglicht Speichern von Verbrauch UND Einspeisung im selben Datensatz

- `prices` Tabelle: Neue optionale Spalte `direction TEXT` ("consumption" | "feed_in", NULL für Gas/Water)
  - Oder: Separate eindeutige Constraint pro (entry_id, direction, valid_from)
  - Ermöglicht zwei unabhängige Preisgeschichte pro Meter

- **Schema-Migration v4**:
  - `ALTER TABLE readings ADD COLUMN feed_in_reading REAL DEFAULT NULL`
  - `ALTER TABLE prices ADD COLUMN direction TEXT DEFAULT NULL`

- Backward-Kompatibilität: `direction IS NULL` = Verbrauch (wie Gas/Water)

### 6. **Translations ([strings.json](gas-water-meter/custom_components/gas_water_meter/strings.json), DE/EN)**

- `config` → `step` → `user` → `data_description`: "Electricity" Meter-Type hinzufügen
- Sensor-Keys für Electricity (neue `translation_key`):
  - `electricity_reading`, `electricity_consumption`, `electricity_{sensor}` o.ä.
- Device name: "Strom" / "Electricity"
- Operator-Kontext (User-freundliche Beschreibungen für Einspeisung vs. Verbrauch)

### 7. **[services.yaml](gas-water-meter/custom_components/gas_water_meter/services.yaml) + Service-Handler — Keine Änderungen**

- `record_reading`, `set_price` etc. arbeiten bereits generisch (meter_type in-dependent)
- Service-Dokumentation aktualisieren: "Gilt für Gas, Wasser und Elektrizität" o.ä.

### 8. **Manifest & Versionsverwaltung**

- [manifest.json](gas-water-meter/custom_components/gas_water_meter/manifest.json): Version auf 0.2.0 erhöhen (neuer Meter-Typ + DB-Schema = Minor Version Bump)
- [config.yaml](gas-water-meter/config.yaml): Version auf 0.2.0 erhöhen
- [CHANGELOG.md](CHANGELOG.md) (root) + [CHANGELOG.md](gas-water-meter/CHANGELOG.md):
  ```
  ## [0.2.0] - YYYY-MM-DD
  ### Added
  - New "Electricity" meter type with dual-channel support (consumption + feed-in)
  - Up to 26 electricity sensors per meter (Home Assistant Energy Dashboard compatible)
  - Separate tariffs and base fees for consumption and feed-in per meter
  - Database schema v4: Support for feed_in readings and directional pricing

  ### Changed
  - Database migration: Added feed_in_reading and direction columns
  ```
- [.cursorrules](.cursorrules) aktualisieren: Electricity zu Meter-Typ-Liste und DB-Schema-Version (v4) hinzufügen

### 9. **Tests schreiben** — ~20-24 neue Tests

- [tests/conftest.py](tests/conftest.py): Zwei Fixtures hinzufügen
  ```python
  MOCK_ELECTRICITY_CONFIG = {
      CONF_METER_TYPE: METER_TYPE_ELECTRICITY,
      CONF_METER_NAME: "Electricity - Consumption",
      CONF_METER_NUMBER: "ELEC-12345",
      CONF_CURRENCY: "EUR",
  }

  MOCK_ELECTRICITY_DUAL_CONFIG = {
      CONF_METER_TYPE: METER_TYPE_ELECTRICITY,
      CONF_METER_NAME: "Electricity - Consumption + Feed-in",
      CONF_METER_NUMBER: "ELEC-67890",
      CONF_CURRENCY: "EUR",
      # Optional: has_feed_in: True
  }
  ```

- [tests/test_sensor.py](tests/test_sensor.py):
  - `test_electricity_consumption_sensors()` — Consumption-Meter hat 13 Sensoren
  - `test_electricity_feed_in_sensors()` — Feed-in-Meter hat 13 Sensoren
  - `test_electricity_dual_sensors()` — Dual-Meter hat 26 Sensoren
  - Sensor-Keys und Device Classes validieren

- [tests/test_coordinator.py](tests/test_coordinator.py):
  - `test_electricity_consumption_cost()` — `consumption_kWh × price_ct/kWh ÷ 100 + grundgebühr`
  - `test_electricity_feed_in_revenue()` — Feed-in Revenue (negative costs)
  - `test_electricity_dual_calculation()` — Kombinierte Verbrauch + Feed-in
  - `test_electricity_projections()` — Hochrechnung (beide Kanäle)
  - `test_electricity_meter_change()` — Zähler wechsel detection (Verbrauch + Feed-in)
  - `test_dual_pricing()` — Unterschiedliche Preise für Verbrauch/Einspeisung

- [tests/test_config_flow.py](tests/test_config_flow.py):
  - `test_electricity_config_flow()` — Electricity in Step 1 auswählen
  - `test_electricity_unique_id()` — Eindeutigkeit prüfen
  - `test_electricity_feed_in_config()` — Optional Feed-in Selektion

- [tests/test_db.py](tests/test_db.py):
  - `test_electricity_readings_crud()` — CRUD mit feed_in_reading Feld
  - `test_schema_migration_v4()` — Migration feed_in_reading + direction
  - `test_directional_prices()` — Preis-CRUD mit direction="feed_in"

- [tests/test_services.py](tests/test_services.py):
  - `test_record_electricity_consumption()` — Service für Consumption
  - `test_record_electricity_feed_in()` — Service für Feed-in (optional)
  - `test_set_consumption_price()` — Preis Verbrauch
  - `test_set_feed_in_price()` — Preis Einspeisung

### 10. **Frontend/WebSocket ([websocket.py](gas-water-meter/custom_components/gas_water_meter/websocket.py)) — Keine Änderungen**

- Bestehende `add_reading`, `add_price`, `get_statistics` arbeiten bereits generisch
- Meter-Typ wird auto-erkannt von config_entry

### 11. **Dokumentation** ([DOCS.md](gas-water-meter/DOCS.md))

- Neue Sektion "Electricity Meters" hinzufügen
- Setup-Beispiel: Zwei separate Elektrizitäts-Meter (Verbrauch + Einspeisung)
- Tarif-Strukturbeispiel (Grundgebühr + ct/kWh)
- Energy Dashboard Integration (welche Sensoren verwenden)

---

## Verification

- **Tests laufen**: `pytest tests/ -q` — alle Tests sollten passen, inklusive neuer Electricity Tests (>290 Tests total)
- **Coverage**: `pytest tests/ --cov=gas-water-meter/custom_components/gas_water_meter --cov-report=term-missing` — mindestens 14 neue Tests für Electricity Coverage
- **Linting**: `ruff check gas-water-meter/custom_components/ tests/` — alle Linting-Regeln einhalten
- **Format**: `ruff format gas-water-meter/custom_components/ tests/` — Code-Style konsistent
- **Config Flow**: Manuelles Testen im Home Assistant UI:
  - Meter-Typ "Electricity" auswählen
  - Tarif setzen (z.B. 30 ct/kWh + 10 EUR Grundgebühr)
  - Zählerstand erfassen (z.B. 1000 kWh)
  - Sensoren im Energy Dashboard sichtbar & Kosten korrekt berechnet
- **Energie-Dashboard**: Electricity Sensoren als "Strom" verfügbar & summiert mit anderen Energiequellen

---

## Design Decisions

- **Ein Meter mit zwei optionalen Zählerständen**: Ein config entry kann Verbrauch und/oder Einspeisung tracken — flexibel für verschiedene Zähler-Setups (nur Verbrauch, nur Einspeisung, oder Hybrid-Zähler)
- **Zwei unabhängige Preislinien**: Separate Tarife und Grundgebühren für Consumption vs. Feed-in, historisiert in derselben pricing-Tabelle mit neuer `direction` Spalte
- **13 oder 26 Sensoren pro Meter**: Abhängig von Konfiguration. Kein Overhead für Consumption-Only Meter (13 Sensoren wie Water)
- **DB-Schema v4 Migration**: `feed_in_reading` und `direction` Columns mit Backward-Kompatibilität (NULL = Verbrauch/Gas/Water)
- **Feed-in als "Negative Costs"**: Einspeisung wird als negative Kosten in `last_period_cost` etc. dargestellt (Ertrag statt Kosten)
- **Keine Breaking Changes**: Electricity ist zusätzlich, bestehende Gas/Water Meter funktionieren unverändert

import { LitElement, html, css } from "lit";
import { Chart, registerables } from "chart.js";

Chart.register(...registerables);

const DOMAIN = "gas_water_meter";

/** Translations keyed by language code. English is the fallback. */
const TRANSLATIONS = {
  en: {
    panel_title: "Gas & Water Meter",
    sidebar_alt: "Gas & Water",
    no_meters: "No meters configured. Please set up a meter in Integrations first.",
    tab_entry: "Entry",
    tab_history: "History",
    tab_prices: "Prices",
    tab_chart: "Chart",
    record_reading: "Record reading",
    photo_optional: "Photo (optional)",
    processing: "Processing...",
    ocr_detected: "OCR detected",
    confidence: "Confidence",
    reading_label: "Meter reading (m\u00b3)",
    reading_placeholder: "e.g. 12345.678",
    meter_number_label: "Meter number",
    meter_number_placeholder: "e.g. GAS-12345",
    datetime_label: "Date / Time",
    save: "Save",
    cancel: "Cancel",
    history_title: "Reading history",
    no_readings: "No readings recorded yet.",
    col_date: "Date",
    col_reading: "Reading",
    col_consumption: "Consumption",
    col_meter_nr: "Meter no.",
    col_photo: "Photo",
    col_actions: "Actions",
    edit: "Edit",
    delete: "Delete",
    edit_reading_title: "Edit reading",
    confirm_delete_reading: "Really delete this reading?",
    price_title: "Record price",
    price_label: "Price per m\u00b3",
    price_placeholder: "e.g. 1.85",
    valid_from: "Valid from",
    valid_to: "Valid to (empty = currently active)",
    price_history: "Price history",
    no_prices: "No prices recorded yet.",
    col_valid_from: "Valid from",
    col_valid_to: "Valid to",
    col_price: "Price/m\u00b3",
    col_currency: "Currency",
    open: "open",
    edit_price_title: "Edit price",
    confirm_delete_price: "Really delete this price?",
    chart_title: "Consumption chart",
    chart_min_readings: "At least 2 readings are required for a chart.",
    chart_consumption: "Consumption (m\u00b3)",
    chart_reading: "Meter reading (m\u00b3)",
    err_invalid_reading: "Please enter a valid meter reading.",
    err_invalid_price: "Please enter a valid price.",
    err_file_too_large: "File is too large ({size} MB). Maximum allowed: 20 MB.",
    err_too_many_pixels: "Image has too many pixels ({mp} MP). Maximum allowed: {max} MP.",
    err_upload_failed: "Upload failed.",
  },
  de: {
    panel_title: "Gas & Wasser",
    sidebar_alt: "Gas & Wasser",
    no_meters: "Keine Z\u00e4hler konfiguriert. Bitte richten Sie zuerst einen Z\u00e4hler in den Integrationen ein.",
    tab_entry: "Erfassung",
    tab_history: "Historie",
    tab_prices: "Preise",
    tab_chart: "Grafik",
    record_reading: "Z\u00e4hlerstand erfassen",
    photo_optional: "Foto (optional)",
    processing: "Wird verarbeitet...",
    ocr_detected: "OCR erkannt",
    confidence: "Konfidenz",
    reading_label: "Z\u00e4hlerstand (m\u00b3)",
    reading_placeholder: "z.B. 12345.678",
    meter_number_label: "Z\u00e4hlernummer",
    meter_number_placeholder: "z.B. GAS-12345",
    datetime_label: "Datum / Uhrzeit",
    save: "Speichern",
    cancel: "Abbrechen",
    history_title: "Ablesehistorie",
    no_readings: "Noch keine Ablesungen vorhanden.",
    col_date: "Datum",
    col_reading: "Z\u00e4hlerstand",
    col_consumption: "Verbrauch",
    col_meter_nr: "Z\u00e4hlernr.",
    col_photo: "Foto",
    col_actions: "Aktionen",
    edit: "Bearbeiten",
    delete: "L\u00f6schen",
    edit_reading_title: "Ablesung bearbeiten",
    confirm_delete_reading: "Ablesung wirklich l\u00f6schen?",
    price_title: "Preis erfassen",
    price_label: "Preis pro m\u00b3",
    price_placeholder: "z.B. 1.85",
    valid_from: "G\u00fcltig ab",
    valid_to: "G\u00fcltig bis (leer = aktuell g\u00fcltig)",
    price_history: "Preishistorie",
    no_prices: "Noch keine Preise erfasst.",
    col_valid_from: "G\u00fcltig ab",
    col_valid_to: "G\u00fcltig bis",
    col_price: "Preis/m\u00b3",
    col_currency: "W\u00e4hrung",
    open: "offen",
    edit_price_title: "Preis bearbeiten",
    confirm_delete_price: "Preis wirklich l\u00f6schen?",
    chart_title: "Verbrauchsgrafik",
    chart_min_readings: "Mindestens 2 Ablesungen f\u00fcr eine Grafik erforderlich.",
    chart_consumption: "Verbrauch (m\u00b3)",
    chart_reading: "Z\u00e4hlerstand (m\u00b3)",
    err_invalid_reading: "Bitte einen g\u00fcltigen Z\u00e4hlerstand eingeben.",
    err_invalid_price: "Bitte einen g\u00fcltigen Preis eingeben.",
    err_file_too_large: "Die Datei ist zu gro\u00df ({size} MB). Maximal erlaubt: 20 MB.",
    err_too_many_pixels: "Das Bild hat zu viele Pixel ({mp} MP). Maximal erlaubt: {max} MP.",
    err_upload_failed: "Upload fehlgeschlagen.",
  },
};

class GasWaterMeterPanel extends LitElement {
  static properties = {
    hass: { type: Object },
    narrow: { type: Boolean },
    panel: { type: Object },
    _meters: { state: true },
    _selectedMeter: { state: true },
    _readings: { state: true },
    _prices: { state: true },
    _stats: { state: true },
    _tab: { state: true },
    _uploading: { state: true },
    _uploadResult: { state: true },
    _editReading: { state: true },
    _editPrice: { state: true },
  };

  constructor() {
    super();
    this._meters = [];
    this._selectedMeter = null;
    this._readings = [];
    this._prices = [];
    this._stats = [];
    this._tab = "readings";
    this._uploading = false;
    this._uploadResult = null;
    this._editReading = null;
    this._editPrice = null;
  }

  /** Return the user's HA language (e.g. "de", "en"). */
  get _lang() {
    return this.hass?.language || "en";
  }

  /** Translate a key using the user's language, falling back to English. */
  _t(key, params) {
    const lang = this._lang;
    const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
    let str = dict[key] ?? TRANSLATIONS.en[key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        str = str.replace(`{${k}}`, v);
      }
    }
    return str;
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadMeters();
    this._replaceSidebarIcon();
  }

  /**
   * Replace the MDI sidebar icon with the custom grayscale icon image.
   * HA's sidebar only supports MDI icon strings natively, so we swap the
   * <ha-icon> element for an <img> pointing to our static grayscale PNG.
   */
  _replaceSidebarIcon() {
    const ICON_URL = "/gas_water_meter_panel/icon_gray.png";
    const PANEL_URL = "gas-water-meter";
    const IMG_SIZE = "24px";

    const tryReplace = (attempts = 0) => {
      if (attempts > 20) return; // give up after ~10 s

      const haMain = document.querySelector("home-assistant")
        ?.shadowRoot?.querySelector("home-assistant-main");
      const sidebar = haMain?.shadowRoot?.querySelector("ha-sidebar");
      if (!sidebar?.shadowRoot) {
        setTimeout(() => tryReplace(attempts + 1), 500);
        return;
      }

      const link = sidebar.shadowRoot.querySelector(
        `a[data-panel="${PANEL_URL}"], a[href="/${PANEL_URL}"]`
      );
      if (!link) {
        setTimeout(() => tryReplace(attempts + 1), 500);
        return;
      }

      const icon = link.querySelector("ha-icon") || link.querySelector("ha-svg-icon");
      if (!icon) {
        setTimeout(() => tryReplace(attempts + 1), 500);
        return;
      }

      // Already replaced?
      if (icon.tagName === "IMG") return;

      const img = document.createElement("img");
      img.src = ICON_URL;
      img.alt = this._t("sidebar_alt");
      img.style.width = IMG_SIZE;
      img.style.height = IMG_SIZE;
      img.style.display = "block";
      img.slot = icon.slot || "";
      icon.replaceWith(img);
    };

    requestAnimationFrame(() => tryReplace());
  }

  updated(changed) {
    if (changed.has("_stats") && this._tab === "chart") {
      this.updateComplete.then(() => this._renderChart());
    }
  }

  // ---- Data loading ----

  async _ws(type, data = {}) {
    return this.hass.connection.sendMessagePromise({
      type: `${DOMAIN}/${type}`,
      ...data,
    });
  }

  async _loadMeters() {
    try {
      const res = await this._ws("list_meters");
      this._meters = res.meters || [];
      if (this._meters.length && !this._selectedMeter) {
        this._selectedMeter = this._meters[0];
        this._loadData();
      }
    } catch (e) {
      console.error("Failed to load meters", e);
    }
  }

  async _loadData() {
    if (!this._selectedMeter) return;
    const eid = this._selectedMeter.entry_id;
    const [rRes, pRes, sRes] = await Promise.all([
      this._ws("get_readings", { entry_id: eid }),
      this._ws("get_prices", { entry_id: eid }),
      this._ws("get_statistics", { entry_id: eid }),
    ]);
    this._readings = rRes.readings || [];
    this._prices = pRes.prices || [];
    this._stats = sRes.statistics || [];
  }

  // ---- Render ----

  render() {
    return html`
      <div class="panel">
        <div class="header">
          <h1>${this._t("panel_title")}</h1>
        </div>
        ${this._meters.length === 0
          ? html`<p class="empty">${this._t("no_meters")}</p>`
          : html`
              ${this._renderMeterTabs()}
              ${this._renderTabBar()}
              <div class="content">${this._renderTabContent()}</div>
            `}
      </div>
    `;
  }

  _renderMeterTabs() {
    return html`
      <div class="meter-tabs">
        ${this._meters.map(
          (m) => html`
            <button
              class="meter-tab ${this._selectedMeter?.entry_id === m.entry_id ? "active" : ""}"
              @click=${() => this._selectMeter(m)}
            >
              <ha-icon .icon=${m.meter_type === "gas" ? "mdi:meter-gas" : "mdi:water"}></ha-icon>
              ${m.meter_name}
            </button>
          `
        )}
      </div>
    `;
  }

  _renderTabBar() {
    const tabs = [
      { id: "readings", label: this._t("tab_entry"), icon: "mdi:plus-circle" },
      { id: "history", label: this._t("tab_history"), icon: "mdi:table" },
      { id: "prices", label: this._t("tab_prices"), icon: "mdi:currency-eur" },
      { id: "chart", label: this._t("tab_chart"), icon: "mdi:chart-bar" },
    ];
    return html`
      <div class="tab-bar">
        ${tabs.map(
          (t) => html`
            <button class="tab ${this._tab === t.id ? "active" : ""}" @click=${() => this._switchTab(t.id)}>
              <ha-icon .icon=${t.icon}></ha-icon>
              <span>${t.label}</span>
            </button>
          `
        )}
      </div>
    `;
  }

  _renderTabContent() {
    switch (this._tab) {
      case "readings":
        return this._renderReadingForm();
      case "history":
        return this._renderHistoryTable();
      case "prices":
        return this._renderPricesTab();
      case "chart":
        return this._renderChartTab();
      default:
        return html``;
    }
  }

  // ---- Reading Form ----

  _renderReadingForm() {
    return html`
      <div class="card">
        <h2>${this._t("record_reading")}</h2>
        <div class="form">
          <div class="upload-area">
            <label>${this._t("photo_optional")}</label>
            <input type="file" accept="image/*,.heic,.heif" capture="environment" id="photo-input" @change=${this._onPhotoSelected} />
            ${this._uploading ? html`<div class="spinner">${this._t("processing")}</div>` : ""}
            ${this._uploadResult?.image_path
              ? html`<img class="preview" src="/local/gas_water_meter_media" alt="Preview" style="display:none" />`
              : ""}
            ${this._uploadResult?.ocr_reading != null
              ? html`<div class="ocr-hint">${this._t("ocr_detected")}: ${this._uploadResult.ocr_reading} (${this._t("confidence")}: ${Math.round(this._uploadResult.ocr_confidence * 100)}%)</div>`
              : ""}
          </div>
          <label>${this._t("reading_label")}</label>
          <input type="number" step="0.001" id="reading-value"
            .value=${this._uploadResult?.ocr_reading ?? ""}
            placeholder=${this._t("reading_placeholder")} />
          <label>${this._t("meter_number_label")}</label>
          <input type="text" id="reading-meter-nr"
            .value=${this._uploadResult?.ocr_meter_number ?? this._selectedMeter?.meter_number ?? ""}
            placeholder=${this._t("meter_number_placeholder")} />
          <label>${this._t("datetime_label")}</label>
          <input type="datetime-local" id="reading-timestamp"
            .value=${this._formatDatetimeLocal(this._uploadResult?.exif_datetime)} />
          <button class="primary" @click=${this._submitReading}>${this._t("save")}</button>
        </div>
      </div>
    `;
  }

  async _onPhotoSelected(e) {
    const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB
    const MAX_MEGAPIXELS = 21;

    const file = e.target.files?.[0];
    if (!file || !this._selectedMeter) return;

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      alert(this._t("err_file_too_large", { size: (file.size / 1024 / 1024).toFixed(1) }));
      e.target.value = "";
      return;
    }

    // Validate image resolution
    try {
      const megapixels = await this._getImageMegapixels(file);
      if (megapixels > MAX_MEGAPIXELS) {
        alert(this._t("err_too_many_pixels", { mp: megapixels.toFixed(1), max: MAX_MEGAPIXELS }));
        e.target.value = "";
        return;
      }
    } catch (err) {
      console.warn("Could not check image resolution", err);
    }

    this._uploading = true;
    this._uploadResult = null;
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("entry_id", this._selectedMeter.entry_id);
      const resp = await fetch(`/api/${DOMAIN}/upload_image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${this.hass.auth.data.access_token}` },
        body: form,
      });
      if (resp.ok) {
        this._uploadResult = await resp.json();
        this.requestUpdate();
      } else {
        const err = await resp.json().catch(() => ({}));
        alert(err.error || this._t("err_upload_failed"));
      }
    } catch (err) {
      console.error("Upload failed", err);
    }
    this._uploading = false;
  }

  _getImageMegapixels(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        const mp = (img.width * img.height) / 1_000_000;
        URL.revokeObjectURL(url);
        resolve(mp);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("Could not load image"));
      };
      img.src = url;
    });
  }

  async _submitReading() {
    const reading = parseFloat(this.shadowRoot.getElementById("reading-value")?.value);
    if (isNaN(reading)) {
      alert(this._t("err_invalid_reading"));
      return;
    }
    const meterNr = this.shadowRoot.getElementById("reading-meter-nr")?.value || "";
    const tsInput = this.shadowRoot.getElementById("reading-timestamp")?.value;
    const timestamp = tsInput ? new Date(tsInput).toISOString() : undefined;

    await this._ws("add_reading", {
      entry_id: this._selectedMeter.entry_id,
      reading,
      meter_number: meterNr,
      timestamp,
      image_path: this._uploadResult?.image_path,
    });

    // Reset form
    this._uploadResult = null;
    const photoInput = this.shadowRoot.getElementById("photo-input");
    if (photoInput) photoInput.value = "";
    const readingInput = this.shadowRoot.getElementById("reading-value");
    if (readingInput) readingInput.value = "";
    const tsEl = this.shadowRoot.getElementById("reading-timestamp");
    if (tsEl) tsEl.value = "";

    await this._loadData();
  }

  // ---- History Table ----

  _renderHistoryTable() {
    return html`
      <div class="card">
        <h2>${this._t("history_title")}</h2>
        ${this._readings.length === 0
          ? html`<p class="empty">${this._t("no_readings")}</p>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>${this._t("col_date")}</th>
                    <th>${this._t("col_reading")}</th>
                    <th>${this._t("col_consumption")}</th>
                    <th>${this._t("col_meter_nr")}</th>
                    <th>${this._t("col_photo")}</th>
                    <th>${this._t("col_actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._readings
                    .slice()
                    .reverse()
                    .map((r, i, arr) => {
                      const prev = i < arr.length - 1 ? arr[i + 1] : null;
                      const consumption = prev ? (r.reading - prev.reading).toFixed(3) : "-";
                      return html`
                        <tr>
                          <td>${this._fmtDate(r.timestamp)}</td>
                          <td>${r.reading.toFixed(3)}</td>
                          <td>${consumption}</td>
                          <td>${r.meter_number}</td>
                          <td>${r.image_path ? html`<ha-icon icon="mdi:camera"></ha-icon>` : ""}</td>
                          <td class="actions">
                            <button class="icon-btn" title=${this._t("edit")} @click=${() => this._startEditReading(r)}>
                              <ha-icon icon="mdi:pencil"></ha-icon>
                            </button>
                            <button class="icon-btn danger" title=${this._t("delete")} @click=${() => this._deleteReading(r.id)}>
                              <ha-icon icon="mdi:delete"></ha-icon>
                            </button>
                          </td>
                        </tr>
                      `;
                    })}
                </tbody>
              </table>
            `}
      </div>
      ${this._editReading ? this._renderEditReadingDialog() : ""}
    `;
  }

  _renderEditReadingDialog() {
    const r = this._editReading;
    return html`
      <div class="dialog-overlay" @click=${this._cancelEditReading}>
        <div class="dialog" @click=${(e) => e.stopPropagation()}>
          <h3>${this._t("edit_reading_title")}</h3>
          <label>${this._t("reading_label")}</label>
          <input type="number" step="0.001" id="edit-reading-value" .value=${r.reading} />
          <label>${this._t("meter_number_label")}</label>
          <input type="text" id="edit-reading-nr" .value=${r.meter_number} />
          <label>${this._t("datetime_label")}</label>
          <input type="datetime-local" id="edit-reading-ts" .value=${this._formatDatetimeLocal(r.timestamp)} />
          <div class="dialog-actions">
            <button @click=${this._cancelEditReading}>${this._t("cancel")}</button>
            <button class="primary" @click=${this._saveEditReading}>${this._t("save")}</button>
          </div>
        </div>
      </div>
    `;
  }

  _startEditReading(r) {
    this._editReading = { ...r };
  }
  _cancelEditReading() {
    this._editReading = null;
  }
  async _saveEditReading() {
    const reading = parseFloat(this.shadowRoot.getElementById("edit-reading-value")?.value);
    const meterNr = this.shadowRoot.getElementById("edit-reading-nr")?.value;
    const tsInput = this.shadowRoot.getElementById("edit-reading-ts")?.value;
    const timestamp = tsInput ? new Date(tsInput).toISOString() : undefined;
    await this._ws("update_reading", {
      reading_id: this._editReading.id,
      reading: isNaN(reading) ? undefined : reading,
      meter_number: meterNr,
      timestamp,
    });
    this._editReading = null;
    await this._loadData();
  }
  async _deleteReading(id) {
    if (!confirm(this._t("confirm_delete_reading"))) return;
    await this._ws("delete_reading", { reading_id: id });
    await this._loadData();
  }

  // ---- Prices Tab ----

  _renderPricesTab() {
    return html`
      <div class="card">
        <h2>${this._t("price_title")}</h2>
        <div class="form">
          <label>${this._t("price_label")} (${this._selectedMeter?.currency || "EUR"})</label>
          <input type="number" step="0.01" id="price-value" placeholder=${this._t("price_placeholder")} />
          <label>${this._t("valid_from")}</label>
          <input type="date" id="price-from" .value=${new Date().toISOString().slice(0, 10)} />
          <label>${this._t("valid_to")}</label>
          <input type="date" id="price-to" />
          <button class="primary" @click=${this._submitPrice}>${this._t("save")}</button>
        </div>
      </div>
      <div class="card">
        <h2>${this._t("price_history")}</h2>
        ${this._prices.length === 0
          ? html`<p class="empty">${this._t("no_prices")}</p>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>${this._t("col_valid_from")}</th>
                    <th>${this._t("col_valid_to")}</th>
                    <th>${this._t("col_price")}</th>
                    <th>${this._t("col_currency")}</th>
                    <th>${this._t("col_actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._prices
                    .slice()
                    .reverse()
                    .map(
                      (p) => html`
                        <tr>
                          <td>${p.valid_from}</td>
                          <td>${p.valid_to || this._t("open")}</td>
                          <td>${p.price_per_unit.toFixed(4)}</td>
                          <td>${p.currency}</td>
                          <td class="actions">
                            <button class="icon-btn" title=${this._t("edit")} @click=${() => this._startEditPrice(p)}>
                              <ha-icon icon="mdi:pencil"></ha-icon>
                            </button>
                            <button class="icon-btn danger" title=${this._t("delete")} @click=${() => this._deletePrice(p.id)}>
                              <ha-icon icon="mdi:delete"></ha-icon>
                            </button>
                          </td>
                        </tr>
                      `
                    )}
                </tbody>
              </table>
            `}
      </div>
      ${this._editPrice ? this._renderEditPriceDialog() : ""}
    `;
  }

  _renderEditPriceDialog() {
    const p = this._editPrice;
    return html`
      <div class="dialog-overlay" @click=${this._cancelEditPrice}>
        <div class="dialog" @click=${(e) => e.stopPropagation()}>
          <h3>${this._t("edit_price_title")}</h3>
          <label>${this._t("price_label")}</label>
          <input type="number" step="0.01" id="edit-price-value" .value=${p.price_per_unit} />
          <label>${this._t("valid_from")}</label>
          <input type="date" id="edit-price-from" .value=${p.valid_from} />
          <label>${this._t("valid_to")}</label>
          <input type="date" id="edit-price-to" .value=${p.valid_to || ""} />
          <div class="dialog-actions">
            <button @click=${this._cancelEditPrice}>${this._t("cancel")}</button>
            <button class="primary" @click=${this._saveEditPrice}>${this._t("save")}</button>
          </div>
        </div>
      </div>
    `;
  }

  async _submitPrice() {
    const price = parseFloat(this.shadowRoot.getElementById("price-value")?.value);
    if (isNaN(price)) {
      alert(this._t("err_invalid_price"));
      return;
    }
    const validFrom = this.shadowRoot.getElementById("price-from")?.value;
    const validTo = this.shadowRoot.getElementById("price-to")?.value || null;
    await this._ws("add_price", {
      entry_id: this._selectedMeter.entry_id,
      price_per_unit: price,
      valid_from: validFrom,
      valid_to: validTo,
    });
    this.shadowRoot.getElementById("price-value").value = "";
    this.shadowRoot.getElementById("price-to").value = "";
    await this._loadData();
  }

  _startEditPrice(p) {
    this._editPrice = { ...p };
  }
  _cancelEditPrice() {
    this._editPrice = null;
  }
  async _saveEditPrice() {
    const price = parseFloat(this.shadowRoot.getElementById("edit-price-value")?.value);
    const from = this.shadowRoot.getElementById("edit-price-from")?.value;
    const to = this.shadowRoot.getElementById("edit-price-to")?.value || null;
    await this._ws("update_price", {
      price_id: this._editPrice.id,
      price_per_unit: isNaN(price) ? undefined : price,
      valid_from: from,
      valid_to: to,
    });
    this._editPrice = null;
    await this._loadData();
  }
  async _deletePrice(id) {
    if (!confirm(this._t("confirm_delete_price"))) return;
    await this._ws("delete_price", { price_id: id });
    await this._loadData();
  }

  // ---- Chart ----

  _renderChartTab() {
    return html`
      <div class="card">
        <h2>${this._t("chart_title")}</h2>
        ${this._stats.length < 2
          ? html`<p class="empty">${this._t("chart_min_readings")}</p>`
          : html`<canvas id="consumption-chart" height="300"></canvas>`}
      </div>
    `;
  }

  _renderChart() {
    const canvas = this.shadowRoot?.getElementById("consumption-chart");
    if (!canvas || this._stats.length < 2) return;

    // Destroy previous chart if any
    if (this._chartInstance) {
      this._chartInstance.destroy();
    }

    const data = this._stats.filter((s) => s.consumption != null);
    const labels = data.map((s) => this._fmtDate(s.timestamp));
    const consumptions = data.map((s) => s.consumption);
    const readings = data.map((s) => s.reading);

    this._chartInstance = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: this._t("chart_consumption"),
            data: consumptions,
            backgroundColor: "rgba(33, 150, 243, 0.6)",
            borderColor: "rgba(33, 150, 243, 1)",
            borderWidth: 1,
            yAxisID: "y",
          },
          {
            label: this._t("chart_reading"),
            data: readings,
            type: "line",
            borderColor: "rgba(255, 152, 0, 1)",
            backgroundColor: "rgba(255, 152, 0, 0.1)",
            fill: true,
            tension: 0.3,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        scales: {
          y: { position: "left", title: { display: true, text: this._t("chart_consumption") } },
          y1: { position: "right", title: { display: true, text: this._t("chart_reading") }, grid: { drawOnChartArea: false } },
        },
      },
    });
  }

  // ---- Helpers ----

  _selectMeter(m) {
    this._selectedMeter = m;
    this._uploadResult = null;
    this._editReading = null;
    this._editPrice = null;
    this._loadData();
  }

  _switchTab(tab) {
    this._tab = tab;
    if (tab === "chart") {
      this.updateComplete.then(() => this._renderChart());
    }
  }

  _fmtDate(iso) {
    if (!iso) return "-";
    try {
      const d = new Date(iso);
      const locale = this._lang === "de" ? "de-DE" : "en-US";
      return d.toLocaleDateString(locale) + " " + d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
    } catch {
      return iso;
    }
  }

  _formatDatetimeLocal(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toISOString().slice(0, 16);
    } catch {
      return "";
    }
  }

  // ---- Styles ----

  static styles = css`
    :host {
      display: block;
      padding: 16px;
      max-width: 960px;
      margin: 0 auto;
      --primary: #03a9f4;
      --primary-dark: #0288d1;
      --danger: #f44336;
      --bg: var(--card-background-color, #fff);
      --text: var(--primary-text-color, #212121);
      --border: var(--divider-color, #e0e0e0);
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--text);
    }
    .header h1 {
      margin: 0 0 16px;
      font-size: 24px;
      font-weight: 400;
    }
    .meter-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }
    .meter-tab {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      border: 1px solid var(--border);
      border-radius: 20px;
      background: var(--bg);
      cursor: pointer;
      font-size: 14px;
      color: var(--text);
      transition: all 0.2s;
    }
    .meter-tab.active {
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }
    .tab-bar {
      display: flex;
      gap: 4px;
      border-bottom: 2px solid var(--border);
      margin-bottom: 16px;
    }
    .tab {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 10px 16px;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 14px;
      color: var(--secondary-text-color, #757575);
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      transition: all 0.2s;
    }
    .tab.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
    }
    .card {
      background: var(--bg);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 16px;
      box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.1));
    }
    .card h2 {
      margin: 0 0 16px;
      font-size: 18px;
      font-weight: 500;
    }
    .form {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .form label {
      font-size: 13px;
      font-weight: 500;
      color: var(--secondary-text-color, #757575);
      margin-top: 4px;
    }
    .form input {
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 15px;
      background: var(--bg);
      color: var(--text);
    }
    .form input:focus {
      outline: none;
      border-color: var(--primary);
    }
    button.primary {
      margin-top: 12px;
      padding: 12px;
      background: var(--primary);
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 15px;
      cursor: pointer;
      transition: background 0.2s;
    }
    button.primary:hover {
      background: var(--primary-dark);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th,
    td {
      padding: 10px 8px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }
    th {
      font-weight: 500;
      color: var(--secondary-text-color, #757575);
      font-size: 12px;
      text-transform: uppercase;
    }
    .actions {
      white-space: nowrap;
    }
    .icon-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px;
      border-radius: 50%;
      color: var(--secondary-text-color, #757575);
    }
    .icon-btn:hover {
      background: rgba(0, 0, 0, 0.05);
    }
    .icon-btn.danger:hover {
      color: var(--danger);
    }
    .dialog-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999;
    }
    .dialog {
      background: var(--bg);
      border-radius: 12px;
      padding: 24px;
      min-width: 320px;
      max-width: 90vw;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .dialog h3 {
      margin: 0 0 8px;
    }
    .dialog label {
      font-size: 13px;
      font-weight: 500;
      color: var(--secondary-text-color, #757575);
    }
    .dialog input {
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 15px;
      background: var(--bg);
      color: var(--text);
    }
    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 12px;
    }
    .dialog-actions button {
      padding: 8px 16px;
      border: 1px solid var(--border);
      border-radius: 6px;
      cursor: pointer;
      background: var(--bg);
      color: var(--text);
    }
    .upload-area {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .ocr-hint {
      font-size: 13px;
      color: var(--primary);
      padding: 6px 10px;
      background: rgba(3, 169, 244, 0.08);
      border-radius: 4px;
    }
    .spinner {
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    .empty {
      color: var(--secondary-text-color, #757575);
      font-style: italic;
    }
    .preview {
      max-width: 200px;
      border-radius: 6px;
    }
    @media (max-width: 600px) {
      :host {
        padding: 8px;
      }
      .tab span {
        display: none;
      }
    }
  `;
}

customElements.define("gas-water-meter-panel", GasWaterMeterPanel);

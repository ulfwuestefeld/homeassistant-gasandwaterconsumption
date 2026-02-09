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
    ocr_not_available: "Tesseract OCR is not installed \u2013 automatic meter reading detection is not available.",
    ocr_no_result: "Meter reading could not be detected automatically \u2013 please enter it manually.",
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
    price_label_gas: "Price (ct/kWh)",
    price_label_water: "Price per m\u00b3",
    price_placeholder_gas: "e.g. 8.45",
    price_placeholder_water: "e.g. 1.85",
    valid_from: "Valid from",
    valid_to: "Valid to (empty = currently active)",
    price_history: "Price history",
    no_prices: "No prices recorded yet.",
    col_valid_from: "Valid from",
    col_valid_to: "Valid to",
    col_price_gas: "ct/kWh",
    col_price_water: "Price/m\u00b3",
    col_currency: "Currency",
    open: "open",
    edit_price_title: "Edit price",
    confirm_delete_price: "Really delete this price?",
    gas_params_title: "Gas conversion factors",
    calorific_value_label: "Calorific value (kWh/m\u00b3)",
    calorific_value_placeholder: "e.g. 11.465",
    condition_factor_label: "Condition factor",
    condition_factor_placeholder: "e.g. 0.9684",
    gas_params_save: "Save conversion factors",
    gas_params_saved: "Conversion factors saved.",
    chart_title: "Monthly consumption",
    chart_min_readings: "At least 2 readings are required for a chart.",
    chart_consumption: "Consumption (m\u00b3)",
    chart_reading: "Meter reading (m\u00b3)",
    chart_no_monthly_data: "Not enough data to calculate monthly consumption.",
    err_invalid_reading: "Please enter a valid meter reading.",
    err_invalid_price: "Please enter a valid price.",
    err_file_too_large: "File is too large ({size} MB). Maximum allowed: 20 MB.",
    err_too_many_pixels: "Image has too many pixels ({mp} MP). Maximum allowed: {max} MP.",
    err_upload_failed: "Upload failed.",
    upload_photo: "Upload photo",
    replace_photo: "Replace photo",
    view_photo: "View",
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
    ocr_not_available: "Tesseract OCR ist nicht installiert \u2013 automatische Z\u00e4hlerstanderkennung nicht verf\u00fcgbar.",
    ocr_no_result: "Z\u00e4hlerstand konnte nicht automatisch erkannt werden \u2013 bitte manuell eingeben.",
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
    price_label_gas: "Preis (ct/kWh)",
    price_label_water: "Preis pro m\u00b3",
    price_placeholder_gas: "z.B. 8,45",
    price_placeholder_water: "z.B. 1,85",
    valid_from: "G\u00fcltig ab",
    valid_to: "G\u00fcltig bis (leer = aktuell g\u00fcltig)",
    price_history: "Preishistorie",
    no_prices: "Noch keine Preise erfasst.",
    col_valid_from: "G\u00fcltig ab",
    col_valid_to: "G\u00fcltig bis",
    col_price_gas: "ct/kWh",
    col_price_water: "Preis/m\u00b3",
    col_currency: "W\u00e4hrung",
    open: "offen",
    edit_price_title: "Preis bearbeiten",
    confirm_delete_price: "Preis wirklich l\u00f6schen?",
    gas_params_title: "Gas-Umrechnungsfaktoren",
    calorific_value_label: "Brennwert (kWh/m\u00b3)",
    calorific_value_placeholder: "z.B. 11,465",
    condition_factor_label: "Zustandszahl",
    condition_factor_placeholder: "z.B. 0,9684",
    gas_params_save: "Umrechnungsfaktoren speichern",
    gas_params_saved: "Umrechnungsfaktoren gespeichert.",
    chart_title: "Monatsverbrauch",
    chart_min_readings: "Mindestens 2 Ablesungen f\u00fcr eine Grafik erforderlich.",
    chart_consumption: "Verbrauch (m\u00b3)",
    chart_reading: "Z\u00e4hlerstand (m\u00b3)",
    chart_no_monthly_data: "Nicht gen\u00fcgend Daten f\u00fcr die Monatsberechnung.",
    err_invalid_reading: "Bitte einen g\u00fcltigen Z\u00e4hlerstand eingeben.",
    err_invalid_price: "Bitte einen g\u00fcltigen Preis eingeben.",
    err_file_too_large: "Die Datei ist zu gro\u00df ({size} MB). Maximal erlaubt: 20 MB.",
    err_too_many_pixels: "Das Bild hat zu viele Pixel ({mp} MP). Maximal erlaubt: {max} MP.",
    err_upload_failed: "Upload fehlgeschlagen.",
    upload_photo: "Foto hochladen",
    replace_photo: "Foto ersetzen",
    view_photo: "Ansehen",
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
    _viewingPhoto: { state: true },
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
    this._viewingPhoto = null;
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

  _toggleMenu() {
    const evt = new Event("hass-toggle-menu", {
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(evt);
  }

  render() {
    return html`
      <div class="panel">
        <div class="toolbar">
          <button class="menu-btn" @click=${this._toggleMenu}>
            <ha-icon icon="mdi:menu"></ha-icon>
          </button>
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
      ${this._renderPhotoLightbox()}
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
              <ha-icon icon=${m.meter_type === "gas" ? "mdi:meter-gas" : "mdi:water"}></ha-icon>
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
              <ha-icon icon=${t.icon}></ha-icon>
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
            <input type="file" accept="image/*,.heic,.heif" id="photo-input" @change=${this._onPhotoSelected} />
            ${this._uploading ? html`<div class="spinner">${this._t("processing")}</div>` : ""}
            ${this._uploadResult?.image_path
              ? html`<img class="preview" src="/local/gas_water_meter_media" alt="Preview" style="display:none" />`
              : ""}
            ${this._uploadResult?.ocr_reading != null
              ? html`<div class="ocr-hint ocr-success">${this._t("ocr_detected")}: ${this._uploadResult.ocr_reading} (${this._t("confidence")}: ${Math.round(this._uploadResult.ocr_confidence * 100)}%)</div>`
              : this._uploadResult && this._uploadResult.ocr_available === false
                ? html`<div class="ocr-hint ocr-warn">${this._t("ocr_not_available")}</div>`
                : this._uploadResult && this._uploadResult.ocr_available === true
                  ? html`<div class="ocr-hint ocr-warn">${this._t("ocr_no_result")}</div>`
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
    const reversed = this._readings.slice().reverse();
    return html`
      <div class="card">
        <h2>${this._t("history_title")}</h2>
        ${this._readings.length === 0
          ? html`<p class="empty">${this._t("no_readings")}</p>`
          : this.narrow
            ? this._renderHistoryCards(reversed)
            : this._renderHistoryDesktop(reversed)}
      </div>
      <!-- Hidden file input for photo upload on existing readings -->
      <input
        type="file"
        accept="image/*,.heic,.heif"
        id="history-photo-input"
        style="display:none"
        @change=${this._onHistoryPhotoSelected}
      />
      ${this._editReading ? this._renderEditReadingDialog() : ""}
    `;
  }

  /** Desktop: classic table layout */
  _renderHistoryDesktop(reversed) {
    return html`
      <div class="table-scroll">
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
            ${reversed.map((r, i, arr) => {
              const prev = i < arr.length - 1 ? arr[i + 1] : null;
              const consumption = prev ? (r.reading - prev.reading).toFixed(3) : "-";
              const imgUrl = this._imageUrl(r.image_path);
              return html`
                <tr>
                  <td>${this._fmtDate(r.timestamp)}</td>
                  <td>${r.reading.toFixed(3)}</td>
                  <td>${consumption}</td>
                  <td>${r.meter_number}</td>
                  <td class="photo-cell">
                    ${imgUrl
                      ? html`<img class="photo-thumb" src=${imgUrl} alt=${this._t("view_photo")}
                               @click=${() => this._openPhotoLightbox(imgUrl)} />`
                      : ""}
                  </td>
                  <td class="actions">
                    <button class="icon-btn" title=${this._t(r.image_path ? "replace_photo" : "upload_photo")} @click=${() => this._startHistoryPhotoUpload(r.id)}>
                      <ha-icon icon="mdi:camera-plus"></ha-icon>
                    </button>
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
      </div>
    `;
  }

  /** Mobile: card-based layout */
  _renderHistoryCards(reversed) {
    return html`
      <div class="reading-cards">
        ${reversed.map((r, i, arr) => {
          const prev = i < arr.length - 1 ? arr[i + 1] : null;
          const consumption = prev ? (r.reading - prev.reading).toFixed(3) : "-";
          const cardImgUrl = this._imageUrl(r.image_path);
          return html`
            <div class="reading-card">
              <div class="reading-card-header">
                <span class="reading-card-date">${this._fmtDate(r.timestamp)}</span>
                ${cardImgUrl
                  ? html`<img class="photo-thumb" src=${cardImgUrl} alt=${this._t("view_photo")}
                           @click=${() => this._openPhotoLightbox(cardImgUrl)} />`
                  : ""}
              </div>
              <div class="reading-card-body">
                <div class="reading-card-row">
                  <span class="reading-card-label">${this._t("col_reading")}</span>
                  <span class="reading-card-value">${r.reading.toFixed(3)} m\u00b3</span>
                </div>
                <div class="reading-card-row">
                  <span class="reading-card-label">${this._t("col_consumption")}</span>
                  <span>${consumption !== "-" ? consumption + " m\u00b3" : "-"}</span>
                </div>
                <div class="reading-card-row">
                  <span class="reading-card-label">${this._t("col_meter_nr")}</span>
                  <span>${r.meter_number}</span>
                </div>
              </div>
              <div class="reading-card-actions">
                <button class="action-btn" @click=${() => this._startHistoryPhotoUpload(r.id)}>
                  <ha-icon icon="mdi:camera-plus"></ha-icon>
                  ${this._t(r.image_path ? "replace_photo" : "upload_photo")}
                </button>
                <button class="action-btn" @click=${() => this._startEditReading(r)}>
                  <ha-icon icon="mdi:pencil"></ha-icon>
                  ${this._t("edit")}
                </button>
                <button class="action-btn danger" @click=${() => this._deleteReading(r.id)}>
                  <ha-icon icon="mdi:delete"></ha-icon>
                  ${this._t("delete")}
                </button>
              </div>
            </div>
          `;
        })}
      </div>
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

  // ---- History Photo Upload ----

  _startHistoryPhotoUpload(readingId) {
    this._uploadForReadingId = readingId;
    const input = this.shadowRoot.getElementById("history-photo-input");
    if (input) {
      input.value = "";
      input.click();
    }
  }

  async _onHistoryPhotoSelected(e) {
    const MAX_FILE_SIZE = 20 * 1024 * 1024;
    const MAX_MEGAPIXELS = 21;
    const file = e.target.files?.[0];
    if (!file || !this._uploadForReadingId || !this._selectedMeter) return;

    if (file.size > MAX_FILE_SIZE) {
      alert(this._t("err_file_too_large", { size: (file.size / 1024 / 1024).toFixed(1) }));
      return;
    }

    try {
      const mp = await this._getImageMegapixels(file);
      if (mp > MAX_MEGAPIXELS) {
        alert(this._t("err_too_many_pixels", { mp: mp.toFixed(1), max: MAX_MEGAPIXELS }));
        return;
      }
    } catch (err) {
      console.warn("Could not check image resolution", err);
    }

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
        const result = await resp.json();
        await this._ws("update_reading", {
          reading_id: this._uploadForReadingId,
          image_path: result.image_path,
        });
        await this._loadData();
      } else {
        const err = await resp.json().catch(() => ({}));
        alert(err.error || this._t("err_upload_failed"));
      }
    } catch (err) {
      console.error("History photo upload failed", err);
    }
    this._uploadForReadingId = null;
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

  get _isGas() {
    return this._selectedMeter?.meter_type === "gas";
  }

  _renderPricesTab() {
    const priceLabel = this._isGas ? this._t("price_label_gas") : `${this._t("price_label_water")} (${this._selectedMeter?.currency || "EUR"})`;
    const pricePlaceholder = this._isGas ? this._t("price_placeholder_gas") : this._t("price_placeholder_water");
    const colPrice = this._isGas ? this._t("col_price_gas") : this._t("col_price_water");

    return html`
      ${this._isGas ? this._renderGasParams() : ""}
      <div class="card">
        <h2>${this._t("price_title")}</h2>
        <div class="form">
          <label>${priceLabel}</label>
          <input type="number" step="0.01" id="price-value" placeholder=${pricePlaceholder} />
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
              <div class="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>${this._t("col_valid_from")}</th>
                      <th>${this._t("col_valid_to")}</th>
                      <th>${colPrice}</th>
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
                            <td>${this._isGas ? "ct/kWh" : p.currency}</td>
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
              </div>
            `}
      </div>
      ${this._editPrice ? this._renderEditPriceDialog() : ""}
    `;
  }

  _renderGasParams() {
    const m = this._selectedMeter;
    return html`
      <div class="card">
        <h2>${this._t("gas_params_title")}</h2>
        <div class="form">
          <label>${this._t("calorific_value_label")}</label>
          <input type="number" step="0.001" id="calorific-value"
            .value=${m?.calorific_value ?? 11.465}
            placeholder=${this._t("calorific_value_placeholder")} />
          <label>${this._t("condition_factor_label")}</label>
          <input type="number" step="0.0001" id="condition-factor"
            .value=${m?.condition_factor ?? 0.9684}
            placeholder=${this._t("condition_factor_placeholder")} />
          <button class="primary" @click=${this._saveGasParams}>${this._t("gas_params_save")}</button>
        </div>
      </div>
    `;
  }

  async _saveGasParams() {
    const cv = parseFloat(this.shadowRoot.getElementById("calorific-value")?.value);
    const cf = parseFloat(this.shadowRoot.getElementById("condition-factor")?.value);
    if (isNaN(cv) || isNaN(cf)) return;
    await this._ws("update_gas_params", {
      entry_id: this._selectedMeter.entry_id,
      calorific_value: cv,
      condition_factor: cf,
    });
    // Update local meter data
    this._selectedMeter = { ...this._selectedMeter, calorific_value: cv, condition_factor: cf };
    alert(this._t("gas_params_saved"));
  }

  _renderEditPriceDialog() {
    const p = this._editPrice;
    const priceLabel = this._isGas ? this._t("price_label_gas") : this._t("price_label_water");
    return html`
      <div class="dialog-overlay" @click=${this._cancelEditPrice}>
        <div class="dialog" @click=${(e) => e.stopPropagation()}>
          <h3>${this._t("edit_price_title")}</h3>
          <label>${priceLabel}</label>
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
    const monthly = this._stats.length >= 2 ? this._aggregateMonthly(this._stats) : [];
    const hasData = monthly.some((m) => m.consumption > 0);
    return html`
      <div class="card">
        <h2>${this._t("chart_title")}</h2>
        ${this._stats.length < 2
          ? html`<p class="empty">${this._t("chart_min_readings")}</p>`
          : !hasData
            ? html`<p class="empty">${this._t("chart_no_monthly_data")}</p>`
            : html`<canvas id="consumption-chart" height="300"></canvas>`}
      </div>
    `;
  }

  /**
   * Aggregate raw statistics into monthly buckets.
   *
   * Each stat entry has: timestamp, reading, consumption (nullable), days, meter_number.
   * When a consumption period spans multiple calendar months, the consumption is
   * distributed proportionally across those months based on the number of days
   * each month contributes to the period.
   *
   * Returns: sorted array of { month, label, consumption, reading }.
   */
  _aggregateMonthly(stats) {
    const MS_PER_DAY = 86_400_000;
    const buckets = {}; // "YYYY-MM" -> { consumption, lastReading, lastTimestamp }

    const ensureBucket = (key, reading, ts) => {
      if (!buckets[key]) {
        buckets[key] = { consumption: 0, lastReading: reading, lastTimestamp: ts };
      } else if (ts > buckets[key].lastTimestamp) {
        buckets[key].lastReading = reading;
        buckets[key].lastTimestamp = ts;
      }
    };

    const monthKey = (d) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;

    for (let i = 0; i < stats.length; i++) {
      const s = stats[i];
      const ts = new Date(s.timestamp);
      const mk = monthKey(ts);
      ensureBucket(mk, s.reading, s.timestamp);

      // Skip entries without consumption (first reading or meter change)
      if (s.consumption == null || i === 0) continue;

      const prev = stats[i - 1];
      const periodStart = new Date(prev.timestamp);
      const periodEnd = ts;
      const totalDays = (periodEnd - periodStart) / MS_PER_DAY;
      if (totalDays <= 0) continue;

      // Same calendar month — add directly
      if (periodStart.getFullYear() === periodEnd.getFullYear() && periodStart.getMonth() === periodEnd.getMonth()) {
        buckets[mk].consumption += s.consumption;
      } else {
        // Distribute consumption proportionally across months
        let cursor = new Date(periodStart);
        while (cursor < periodEnd) {
          const ck = monthKey(cursor);
          // Segment end: first day of next month, or periodEnd, whichever comes first
          const nextMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
          const segEnd = nextMonth < periodEnd ? nextMonth : periodEnd;
          const segStart = cursor < periodStart ? periodStart : cursor;
          const segDays = (segEnd - segStart) / MS_PER_DAY;

          if (segDays > 0) {
            const share = s.consumption * (segDays / totalDays);
            ensureBucket(ck, s.reading, s.timestamp);
            buckets[ck].consumption += share;
          }
          cursor = nextMonth;
        }
      }
    }

    return Object.entries(buckets)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, val]) => ({
        month: key,
        label: this._fmtMonth(key),
        consumption: Math.round(val.consumption * 1000) / 1000,
        reading: val.lastReading,
      }));
  }

  /** Format "YYYY-MM" into a locale-aware month label, e.g. "Jan 2026". */
  _fmtMonth(yearMonth) {
    const [year, month] = yearMonth.split("-");
    const d = new Date(parseInt(year), parseInt(month) - 1, 1);
    const locale = this._lang === "de" ? "de-DE" : "en-US";
    return d.toLocaleDateString(locale, { month: "short", year: "numeric" });
  }

  _renderChart() {
    const canvas = this.shadowRoot?.getElementById("consumption-chart");
    if (!canvas || this._stats.length < 2) return;

    if (this._chartInstance) {
      this._chartInstance.destroy();
    }

    const monthly = this._aggregateMonthly(this._stats);
    if (monthly.length === 0) return;

    const labels = monthly.map((m) => m.label);
    const consumptions = monthly.map((m) => m.consumption);
    const readings = monthly.map((m) => m.reading);

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

  // ---- Photo lightbox ----

  /**
   * Convert an absolute image_path (from the DB) to a URL served by the
   * registered static path /gas_water_meter_media/.
   */
  _imageUrl(imagePath) {
    if (!imagePath) return null;
    const marker = "gas_water_meter";
    const idx = imagePath.lastIndexOf(marker);
    if (idx < 0) return null;
    let rest = imagePath.substring(idx + marker.length);
    // Remove leading separator (/ or \)
    if (rest.startsWith("/") || rest.startsWith("\\")) rest = rest.substring(1);
    // Normalize backslashes for URL
    rest = rest.replace(/\\/g, "/");
    return `/gas_water_meter_media/${rest}`;
  }

  _openPhotoLightbox(url) {
    this._viewingPhoto = url;
  }

  _closePhotoLightbox() {
    this._viewingPhoto = null;
  }

  _renderPhotoLightbox() {
    if (!this._viewingPhoto) return html``;
    return html`
      <div class="lightbox-overlay" @click=${this._closePhotoLightbox}>
        <button class="lightbox-close" @click=${this._closePhotoLightbox}>
          <ha-icon icon="mdi:close"></ha-icon>
        </button>
        <img
          class="lightbox-img"
          src=${this._viewingPhoto}
          alt="Meter photo"
          @click=${(e) => e.stopPropagation()}
        />
      </div>
    `;
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
      if (isNaN(d.getTime())) return "";
      // Use local time components – datetime-local inputs expect local time,
      // NOT UTC.  The previous .toISOString().slice() silently converted to
      // UTC which shifted the displayed time by the user's UTC offset.
      const pad = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
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
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 16px;
    }
    .toolbar h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 400;
      flex: 1;
    }
    .menu-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 8px;
      margin: -8px 0 -8px -8px;
      border-radius: 50%;
      color: var(--text);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .menu-btn:hover {
      background: rgba(0, 0, 0, 0.05);
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
    .table-scroll {
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
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
    /* Ensure ha-icon renders at a visible size in all contexts */
    ha-icon {
      --mdc-icon-size: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    .icon-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 8px;
      border-radius: 50%;
      color: var(--secondary-text-color, #757575);
      min-width: 40px;
      min-height: 40px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    .icon-btn ha-icon {
      --mdc-icon-size: 20px;
    }
    .icon-btn:hover {
      background: rgba(0, 0, 0, 0.05);
    }
    .icon-btn.danger:hover {
      color: var(--danger);
    }
    /* ---- Mobile card layout for readings ---- */
    .reading-cards {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .reading-card {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
    }
    .reading-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-weight: 500;
    }
    .reading-card-date {
      font-size: 13px;
      color: var(--secondary-text-color, #757575);
    }
    .reading-card-body {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 10px;
    }
    .reading-card-row {
      display: flex;
      justify-content: space-between;
      font-size: 14px;
    }
    .reading-card-label {
      color: var(--secondary-text-color, #757575);
      font-size: 13px;
    }
    .reading-card-value {
      font-weight: 600;
      font-size: 16px;
    }
    .reading-card-actions {
      display: flex;
      gap: 8px;
      border-top: 1px solid var(--border);
      padding-top: 10px;
    }
    .action-btn {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 10px 8px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--bg);
      color: var(--text);
      font-size: 12px;
      cursor: pointer;
      min-height: 44px;
    }
    .action-btn:hover {
      background: rgba(0, 0, 0, 0.03);
    }
    .action-btn.danger {
      color: var(--danger);
      border-color: var(--danger);
    }
    .action-btn ha-icon {
      --mdc-icon-size: 18px;
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
      padding: 6px 10px;
      border-radius: 4px;
    }
    .ocr-hint.ocr-success {
      color: var(--primary);
      background: rgba(3, 169, 244, 0.08);
    }
    .ocr-hint.ocr-warn {
      color: var(--warning-color, #ff9800);
      background: rgba(255, 152, 0, 0.08);
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
    /* ---- Photo thumbnails ---- */
    .photo-cell {
      text-align: center;
    }
    .photo-thumb {
      width: 40px;
      height: 40px;
      object-fit: cover;
      border-radius: 4px;
      cursor: pointer;
      transition: transform 0.2s;
      vertical-align: middle;
    }
    .photo-thumb:hover {
      transform: scale(1.1);
    }
    /* ---- Photo lightbox ---- */
    .lightbox-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.85);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      cursor: pointer;
    }
    .lightbox-close {
      position: absolute;
      top: 16px;
      right: 16px;
      background: rgba(255, 255, 255, 0.2);
      border: none;
      border-radius: 50%;
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      cursor: pointer;
      z-index: 1001;
    }
    .lightbox-close:hover {
      background: rgba(255, 255, 255, 0.3);
    }
    .lightbox-close ha-icon {
      --mdc-icon-size: 24px;
      color: #fff;
    }
    .lightbox-img {
      max-width: 90vw;
      max-height: 90vh;
      object-fit: contain;
      border-radius: 4px;
      cursor: default;
    }
    @media (max-width: 600px) {
      :host {
        padding: 8px;
      }
      .tab-bar {
        justify-content: space-around;
      }
      .tab {
        flex-direction: column;
        padding: 8px 6px;
        font-size: 11px;
        gap: 2px;
      }
      .tab ha-icon {
        --mdc-icon-size: 20px;
      }
    }
  `;
}

customElements.define("gas-water-meter-panel", GasWaterMeterPanel);

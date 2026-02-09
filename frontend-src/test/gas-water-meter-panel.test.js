import { fixture, expect, html } from "@open-wc/testing";
import { setViewport } from "@web/test-runner-commands";

// Stub Home Assistant custom elements that are not available outside HA.
// The stub mirrors real ha-icon: the "icon" property reflects to/from the
// HTML attribute so that both `icon="mdi:foo"` (attribute) and `.icon`
// (property access) work correctly in tests.
if (!customElements.get("ha-icon")) {
  customElements.define(
    "ha-icon",
    class HaIconStub extends HTMLElement {
      static get observedAttributes() {
        return ["icon"];
      }
      get icon() {
        return this.getAttribute("icon");
      }
      set icon(val) {
        if (val != null) this.setAttribute("icon", val);
        else this.removeAttribute("icon");
      }
    }
  );
}

// Import the panel component (registers <gas-water-meter-panel>).
import "../src/gas-water-meter-panel.js";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const MOCK_METER = {
  entry_id: "test_entry_1",
  meter_name: "Gaszähler",
  meter_type: "gas",
  meter_number: "GAS-001",
  currency: "EUR",
};

const MOCK_READINGS = [
  {
    id: 1,
    entry_id: "test_entry_1",
    meter_number: "GAS-001",
    reading: 100.0,
    timestamp: "2025-01-01T10:00:00Z",
    image_path: null,
  },
  {
    id: 2,
    entry_id: "test_entry_1",
    meter_number: "GAS-001",
    reading: 105.5,
    timestamp: "2025-02-01T10:00:00Z",
    image_path: "/config/media/gas_water_meter/test_entry_1/20250201_100000.jpg",
  },
];

function createMockHass(lang = "de", { readings = [], meters = [MOCK_METER], statistics = [] } = {}) {
  return {
    language: lang,
    connection: {
      sendMessagePromise: async (msg) => {
        switch (msg.type) {
          case "gas_water_meter/list_meters":
            return { meters };
          case "gas_water_meter/get_readings":
            return { readings, total: readings.length };
          case "gas_water_meter/get_prices":
            return { prices: [] };
          case "gas_water_meter/get_statistics":
            return { statistics };
          default:
            return {};
        }
      },
    },
    auth: { data: { access_token: "test-token" } },
  };
}

// ---------------------------------------------------------------------------
// Helper – create the panel and wait until it is fully rendered with data.
// ---------------------------------------------------------------------------

async function createPanel({ narrow = false, lang = "de", readings = [], meters, statistics } = {}) {
  const hass = createMockHass(lang, { readings, ...(meters && { meters }), ...(statistics && { statistics }) });

  // connectedCallback fires before Lit commits property bindings,
  // so _loadMeters() called there will fail silently (hass is undefined).
  const el = await fixture(
    html`<gas-water-meter-panel .hass=${hass} ?narrow=${narrow}></gas-water-meter-panel>`
  );

  // Manually trigger data loading now that hass is available.
  await el._loadMeters();

  // _loadData is called (but not awaited) inside _loadMeters.
  // Flush the microtask queue so readings/prices/stats resolve.
  await new Promise((r) => setTimeout(r, 20));
  await el.updateComplete;

  return el;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("gas-water-meter-panel", () => {
  // Reset viewport after tests that change it.
  afterEach(async () => {
    await setViewport({ width: 1024, height: 768 });
  });

  // ------------------------------------------------------------------
  // Sidebar menu button
  // ------------------------------------------------------------------

  describe("sidebar menu button", () => {
    it("always shows the hamburger menu button", async () => {
      const el = await createPanel({ narrow: false });
      const menuBtn = el.shadowRoot.querySelector(".menu-btn");

      expect(menuBtn).to.not.be.null;
      const icon = menuBtn.querySelector("ha-icon");
      expect(icon).to.not.be.null;
      expect(icon.getAttribute("icon")).to.equal("mdi:menu");
    });

    it("shows the hamburger menu on narrow viewports too", async () => {
      const el = await createPanel({ narrow: true });
      const menuBtn = el.shadowRoot.querySelector(".menu-btn");

      expect(menuBtn).to.not.be.null;
    });

    it("dispatches hass-toggle-menu event on click", async () => {
      const el = await createPanel({ narrow: true });
      const menuBtn = el.shadowRoot.querySelector(".menu-btn");

      let firedEvent = null;
      el.addEventListener("hass-toggle-menu", (e) => {
        firedEvent = e;
      });

      menuBtn.click();

      expect(firedEvent).to.not.be.null;
      expect(firedEvent.bubbles).to.be.true;
      expect(firedEvent.composed).to.be.true;
    });
  });

  // ------------------------------------------------------------------
  // Tab labels on mobile viewport
  // ------------------------------------------------------------------

  describe("tab labels on small screens", () => {
    it("tab labels are visible at iPhone viewport width (375px)", async () => {
      await setViewport({ width: 375, height: 812 });
      const el = await createPanel();

      const tabSpans = el.shadowRoot.querySelectorAll(".tab span");
      expect(tabSpans.length).to.equal(4, "expected 4 tab labels");

      for (const span of tabSpans) {
        const style = window.getComputedStyle(span);
        expect(style.display).to.not.equal(
          "none",
          `Tab label "${span.textContent.trim()}" should be visible on mobile`
        );
      }
    });

    it("tab labels are visible at desktop viewport width (1024px)", async () => {
      await setViewport({ width: 1024, height: 768 });
      const el = await createPanel();

      const tabSpans = el.shadowRoot.querySelectorAll(".tab span");
      expect(tabSpans.length).to.equal(4);

      for (const span of tabSpans) {
        const style = window.getComputedStyle(span);
        expect(style.display).to.not.equal("none");
      }
    });

    it("renders all four tab buttons with icons", async () => {
      const el = await createPanel();
      const tabs = el.shadowRoot.querySelectorAll(".tab");

      expect(tabs.length).to.equal(4);
      for (const tab of tabs) {
        expect(tab.querySelector("ha-icon")).to.not.be.null;
        expect(tab.querySelector("span")).to.not.be.null;
      }
    });

    it("tabs switch to vertical layout on mobile", async () => {
      await setViewport({ width: 375, height: 812 });
      const el = await createPanel();

      const tab = el.shadowRoot.querySelector(".tab");
      const style = window.getComputedStyle(tab);
      expect(style.flexDirection).to.equal("column");
    });
  });

  // ------------------------------------------------------------------
  // File upload – no capture attribute
  // ------------------------------------------------------------------

  describe("file upload input", () => {
    it("does NOT have a capture attribute", async () => {
      const el = await createPanel();

      // The reading form is the default tab
      const input = el.shadowRoot.querySelector("#photo-input");
      expect(input).to.not.be.null;
      expect(input.hasAttribute("capture")).to.be.false;
    });

    it("accepts image/*, .heic, and .heif files", async () => {
      const el = await createPanel();
      const input = el.shadowRoot.querySelector("#photo-input");

      expect(input).to.not.be.null;
      const accept = input.getAttribute("accept");
      expect(accept).to.include("image/*");
      expect(accept).to.include(".heic");
      expect(accept).to.include(".heif");
    });

    it("is a file input element", async () => {
      const el = await createPanel();
      const input = el.shadowRoot.querySelector("#photo-input");

      expect(input).to.not.be.null;
      expect(input.getAttribute("type")).to.equal("file");
    });
  });

  // ------------------------------------------------------------------
  // Internationalization
  // ------------------------------------------------------------------

  describe("internationalization", () => {
    it("renders German labels when language is de", async () => {
      const el = await createPanel({ lang: "de" });
      const title = el.shadowRoot.querySelector(".toolbar h1");
      expect(title.textContent).to.equal("Gas & Wasser");
    });

    it("renders English labels when language is en", async () => {
      const el = await createPanel({ lang: "en" });
      const title = el.shadowRoot.querySelector(".toolbar h1");
      expect(title.textContent).to.equal("Gas & Water Meter");
    });

    it("falls back to English for unsupported languages", async () => {
      const el = await createPanel({ lang: "fr" });
      const title = el.shadowRoot.querySelector(".toolbar h1");
      expect(title.textContent).to.equal("Gas & Water Meter");
    });
  });

  // ------------------------------------------------------------------
  // Tab navigation
  // ------------------------------------------------------------------

  describe("tab navigation", () => {
    it("starts on the readings tab", async () => {
      const el = await createPanel();
      const activeTab = el.shadowRoot.querySelector(".tab.active");

      expect(activeTab).to.not.be.null;
      // Lit uses property binding (.icon=), so read the property, not the attribute.
      expect(activeTab.querySelector("ha-icon").icon).to.equal("mdi:plus-circle");
    });

    it("switches tabs on click", async () => {
      const el = await createPanel();
      const tabs = el.shadowRoot.querySelectorAll(".tab");

      // Click History tab (index 1)
      tabs[1].click();
      await el.updateComplete;

      const activeTab = el.shadowRoot.querySelector(".tab.active");
      expect(activeTab.querySelector("ha-icon").icon).to.equal("mdi:table");

      // Content should now show history
      const historyTitle = el.shadowRoot.querySelector(".card h2");
      expect(historyTitle).to.not.be.null;
    });
  });

  // ------------------------------------------------------------------
  // Meter tabs
  // ------------------------------------------------------------------

  describe("meter tabs", () => {
    it("renders the meter tab with correct name", async () => {
      const el = await createPanel();
      const meterTab = el.shadowRoot.querySelector(".meter-tab");

      expect(meterTab).to.not.be.null;
      expect(meterTab.textContent.trim()).to.include("Gaszähler");
    });

    it("marks the selected meter as active", async () => {
      const el = await createPanel();
      const meterTab = el.shadowRoot.querySelector(".meter-tab");

      expect(meterTab.classList.contains("active")).to.be.true;
    });

    it("displays renamed meter names from the WebSocket response", async () => {
      const renamedMeter = {
        ...MOCK_METER,
        meter_name: "5222961 (Gas)",
      };
      const el = await createPanel({ meters: [renamedMeter] });
      const meterTab = el.shadowRoot.querySelector(".meter-tab");

      expect(meterTab).to.not.be.null;
      expect(meterTab.textContent.trim()).to.include("5222961 (Gas)");
    });

    it("displays multiple renamed meter names correctly", async () => {
      const meters = [
        { ...MOCK_METER, entry_id: "e1", meter_name: "5222961 (Gas)" },
        {
          entry_id: "e2",
          meter_name: "8EMTB123501226 (Water)",
          meter_type: "water",
          meter_number: "WAT-001",
          currency: "EUR",
        },
      ];
      const el = await createPanel({ meters });
      const meterTabs = el.shadowRoot.querySelectorAll(".meter-tab");

      expect(meterTabs.length).to.equal(2);
      expect(meterTabs[0].textContent.trim()).to.include("5222961 (Gas)");
      expect(meterTabs[1].textContent.trim()).to.include("8EMTB123501226 (Water)");
    });
  });

  // ------------------------------------------------------------------
  // History – mobile card layout vs. desktop table
  // ------------------------------------------------------------------

  describe("history layout", () => {
    it("shows card layout on mobile (narrow=true) with readings", async () => {
      const el = await createPanel({ narrow: true, readings: MOCK_READINGS });

      // Switch to history tab
      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      // Should render cards, not a table
      const cards = el.shadowRoot.querySelectorAll(".reading-card");
      expect(cards.length).to.equal(2);

      const table = el.shadowRoot.querySelector("table");
      expect(table).to.be.null;
    });

    it("shows table layout on desktop (narrow=false) with readings", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      // Switch to history tab
      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      // Should render table inside a scrollable wrapper
      const tableScroll = el.shadowRoot.querySelector(".table-scroll");
      expect(tableScroll).to.not.be.null;

      const table = tableScroll.querySelector("table");
      expect(table).to.not.be.null;

      const rows = table.querySelectorAll("tbody tr");
      expect(rows.length).to.equal(2);
    });

    it("desktop table has a scrollable wrapper", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const wrapper = el.shadowRoot.querySelector(".table-scroll");
      expect(wrapper).to.not.be.null;
      const style = window.getComputedStyle(wrapper);
      expect(style.overflowX).to.equal("auto");
    });
  });

  // ------------------------------------------------------------------
  // History – action buttons
  // ------------------------------------------------------------------

  describe("history action buttons", () => {
    it("mobile cards have edit, delete, and photo upload buttons", async () => {
      const el = await createPanel({ narrow: true, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const card = el.shadowRoot.querySelector(".reading-card");
      const actionBtns = card.querySelectorAll(".action-btn");

      // 3 action buttons: photo, edit, delete
      expect(actionBtns.length).to.equal(3);
    });

    it("mobile action buttons have adequate touch target (min 44px)", async () => {
      const el = await createPanel({ narrow: true, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const actionBtns = el.shadowRoot.querySelectorAll(".action-btn");
      for (const btn of actionBtns) {
        const style = window.getComputedStyle(btn);
        const minHeight = parseInt(style.minHeight, 10);
        expect(minHeight).to.be.at.least(44, "Touch target should be at least 44px");
      }
    });

    it("desktop table has photo upload, edit, and delete buttons per row", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const actionCells = el.shadowRoot.querySelectorAll("td.actions");
      expect(actionCells.length).to.equal(2);

      // Each row should have 3 icon buttons (photo, edit, delete)
      for (const cell of actionCells) {
        const btns = cell.querySelectorAll(".icon-btn");
        expect(btns.length).to.equal(3);
      }
    });

    it("photo upload button label changes when reading has an image", async () => {
      const el = await createPanel({ narrow: true, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const cards = el.shadowRoot.querySelectorAll(".reading-card");
      // Cards are in reverse order: reading 2 (with image) first, reading 1 (no image) second
      const card1PhotoBtn = cards[0].querySelector(".action-btn"); // reading 2 has image
      const card2PhotoBtn = cards[1].querySelector(".action-btn"); // reading 1 has no image

      expect(card1PhotoBtn.textContent.trim()).to.include("ersetzen");
      expect(card2PhotoBtn.textContent.trim()).to.include("hochladen");
    });
  });

  // ------------------------------------------------------------------
  // History photo upload input
  // ------------------------------------------------------------------

  describe("history photo upload", () => {
    it("has a hidden file input for history photo upload", async () => {
      const el = await createPanel({ narrow: true, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const input = el.shadowRoot.querySelector("#history-photo-input");
      expect(input).to.not.be.null;
      expect(input.getAttribute("type")).to.equal("file");
      expect(input.style.display).to.equal("none");
      expect(input.hasAttribute("capture")).to.be.false;
    });

    it("hidden file input accepts images including HEIC/HEIF", async () => {
      const el = await createPanel({ narrow: true, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const input = el.shadowRoot.querySelector("#history-photo-input");
      const accept = input.getAttribute("accept");
      expect(accept).to.include("image/*");
      expect(accept).to.include(".heic");
      expect(accept).to.include(".heif");
    });
  });

  // ------------------------------------------------------------------
  // Image URL helper
  // ------------------------------------------------------------------

  describe("_imageUrl helper", () => {
    it("converts an absolute image path to a media URL", async () => {
      const el = await createPanel();
      const url = el._imageUrl("/config/media/gas_water_meter/entry1/photo.jpg");
      expect(url).to.equal("/gas_water_meter_media/entry1/photo.jpg");
    });

    it("handles Windows-style backslash paths", async () => {
      const el = await createPanel();
      const url = el._imageUrl("C:\\config\\media\\gas_water_meter\\entry1\\photo.jpg");
      expect(url).to.equal("/gas_water_meter_media/entry1/photo.jpg");
    });

    it("returns null for null or undefined input", async () => {
      const el = await createPanel();
      expect(el._imageUrl(null)).to.be.null;
      expect(el._imageUrl(undefined)).to.be.null;
    });

    it("returns null for a path without the gas_water_meter marker", async () => {
      const el = await createPanel();
      expect(el._imageUrl("/some/other/path/photo.jpg")).to.be.null;
    });
  });

  // ------------------------------------------------------------------
  // _formatDatetimeLocal helper
  // ------------------------------------------------------------------

  describe("_formatDatetimeLocal helper", () => {
    it("returns empty string for null", async () => {
      const el = await createPanel();
      expect(el._formatDatetimeLocal(null)).to.equal("");
    });

    it("returns empty string for undefined", async () => {
      const el = await createPanel();
      expect(el._formatDatetimeLocal(undefined)).to.equal("");
    });

    it("returns empty string for empty string", async () => {
      const el = await createPanel();
      expect(el._formatDatetimeLocal("")).to.equal("");
    });

    it("formats a naive ISO string using local time (no UTC shift)", async () => {
      const el = await createPanel();
      // A naive ISO string should be interpreted as local time and
      // returned as local time -- NOT shifted to UTC.
      const result = el._formatDatetimeLocal("2026-02-08T15:30:00");
      // The browser interprets "2026-02-08T15:30:00" as local time,
      // so the formatted output must also show 15:30 in local time.
      expect(result).to.equal("2026-02-08T15:30");
    });

    it("formats a timezone-aware ISO string as local time", async () => {
      const el = await createPanel();
      // "2026-02-08T15:30:00+01:00" is 14:30 UTC.
      // In the browser's local timezone, the display depends on the
      // browser timezone, but the result must match the local Date components.
      const input = "2026-02-08T15:30:00+01:00";
      const d = new Date(input);
      const pad = (n) => String(n).padStart(2, "0");
      const expected = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
      const result = el._formatDatetimeLocal(input);
      expect(result).to.equal(expected);
    });

    it("returns a string suitable for datetime-local input (YYYY-MM-DDTHH:MM)", async () => {
      const el = await createPanel();
      const result = el._formatDatetimeLocal("2026-06-15T10:00:00");
      expect(result).to.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
    });

    it("returns empty string for invalid date", async () => {
      const el = await createPanel();
      expect(el._formatDatetimeLocal("not-a-date")).to.equal("");
    });
  });

  // ------------------------------------------------------------------
  // Photo thumbnails in history
  // ------------------------------------------------------------------

  describe("photo thumbnails", () => {
    it("desktop table shows a thumbnail for readings with an image", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const thumbs = el.shadowRoot.querySelectorAll(".photo-thumb");
      // Only reading 2 has image_path, so exactly one thumbnail
      expect(thumbs.length).to.equal(1);
      expect(thumbs[0].getAttribute("src")).to.equal(
        "/gas_water_meter_media/test_entry_1/20250201_100000.jpg"
      );
    });

    it("desktop table does not show a thumbnail for readings without an image", async () => {
      const readingsNoImage = [
        { ...MOCK_READINGS[0] },
        { ...MOCK_READINGS[1], image_path: null },
      ];
      const el = await createPanel({ narrow: false, readings: readingsNoImage });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const thumbs = el.shadowRoot.querySelectorAll(".photo-thumb");
      expect(thumbs.length).to.equal(0);
    });

    it("mobile cards show a thumbnail for readings with an image", async () => {
      const el = await createPanel({ narrow: true, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const thumbs = el.shadowRoot.querySelectorAll(".photo-thumb");
      expect(thumbs.length).to.equal(1);
      expect(thumbs[0].getAttribute("src")).to.equal(
        "/gas_water_meter_media/test_entry_1/20250201_100000.jpg"
      );
    });

    it("thumbnail has cursor pointer for clickability", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const thumb = el.shadowRoot.querySelector(".photo-thumb");
      expect(thumb).to.not.be.null;
      const style = window.getComputedStyle(thumb);
      expect(style.cursor).to.equal("pointer");
    });
  });

  // ------------------------------------------------------------------
  // Photo lightbox
  // ------------------------------------------------------------------

  describe("photo lightbox", () => {
    it("is not shown by default", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const overlay = el.shadowRoot.querySelector(".lightbox-overlay");
      expect(overlay).to.be.null;
    });

    it("opens when clicking a photo thumbnail", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const thumb = el.shadowRoot.querySelector(".photo-thumb");
      expect(thumb).to.not.be.null;
      thumb.click();
      await el.updateComplete;

      const overlay = el.shadowRoot.querySelector(".lightbox-overlay");
      expect(overlay).to.not.be.null;

      const img = overlay.querySelector(".lightbox-img");
      expect(img).to.not.be.null;
      expect(img.getAttribute("src")).to.equal(
        "/gas_water_meter_media/test_entry_1/20250201_100000.jpg"
      );
    });

    it("closes when clicking the overlay background", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      // Open lightbox
      el.shadowRoot.querySelector(".photo-thumb").click();
      await el.updateComplete;
      expect(el.shadowRoot.querySelector(".lightbox-overlay")).to.not.be.null;

      // Click overlay to close
      el.shadowRoot.querySelector(".lightbox-overlay").click();
      await el.updateComplete;
      expect(el.shadowRoot.querySelector(".lightbox-overlay")).to.be.null;
    });

    it("closes when clicking the close button", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      // Open lightbox
      el.shadowRoot.querySelector(".photo-thumb").click();
      await el.updateComplete;
      expect(el.shadowRoot.querySelector(".lightbox-overlay")).to.not.be.null;

      // Click close button
      el.shadowRoot.querySelector(".lightbox-close").click();
      await el.updateComplete;
      expect(el.shadowRoot.querySelector(".lightbox-overlay")).to.be.null;
    });

    it("does not close when clicking the lightbox image", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      // Open lightbox
      el.shadowRoot.querySelector(".photo-thumb").click();
      await el.updateComplete;

      // Click the image itself - should NOT close
      el.shadowRoot.querySelector(".lightbox-img").click();
      await el.updateComplete;
      expect(el.shadowRoot.querySelector(".lightbox-overlay")).to.not.be.null;
    });

    it("works from mobile card thumbnails too", async () => {
      const el = await createPanel({ narrow: true, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const thumb = el.shadowRoot.querySelector(".photo-thumb");
      expect(thumb).to.not.be.null;
      thumb.click();
      await el.updateComplete;

      const overlay = el.shadowRoot.querySelector(".lightbox-overlay");
      expect(overlay).to.not.be.null;

      const img = overlay.querySelector(".lightbox-img");
      expect(img).to.not.be.null;
    });

    it("has a close button with an icon", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      el.shadowRoot.querySelector(".photo-thumb").click();
      await el.updateComplete;

      const closeBtn = el.shadowRoot.querySelector(".lightbox-close");
      expect(closeBtn).to.not.be.null;
      const icon = closeBtn.querySelector("ha-icon");
      expect(icon).to.not.be.null;
      expect(icon.icon).to.equal("mdi:close");
    });
  });

  // ------------------------------------------------------------------
  // Reading form elements
  // ------------------------------------------------------------------

  describe("reading form", () => {
    it("renders the reading input field", async () => {
      const el = await createPanel();
      const input = el.shadowRoot.querySelector("#reading-value");
      expect(input).to.not.be.null;
      expect(input.getAttribute("type")).to.equal("number");
    });

    it("renders the meter number input field", async () => {
      const el = await createPanel();
      const input = el.shadowRoot.querySelector("#reading-meter-nr");
      expect(input).to.not.be.null;
    });

    it("renders the datetime input field", async () => {
      const el = await createPanel();
      const input = el.shadowRoot.querySelector("#reading-timestamp");
      expect(input).to.not.be.null;
      expect(input.getAttribute("type")).to.equal("datetime-local");
    });

    it("pre-fills meter number from selected meter", async () => {
      const el = await createPanel();
      const input = el.shadowRoot.querySelector("#reading-meter-nr");
      expect(input.value).to.equal("GAS-001");
    });

    it("renders a save button", async () => {
      const el = await createPanel();
      const saveBtn = el.shadowRoot.querySelector("button.primary");
      expect(saveBtn).to.not.be.null;
      expect(saveBtn.textContent.trim()).to.include("Speichern");
    });

    it("renders the photo upload button", async () => {
      const el = await createPanel();
      const photoInput = el.shadowRoot.querySelector("#photo-input");
      expect(photoInput).to.not.be.null;
    });

    it("reading form card has a title", async () => {
      const el = await createPanel();
      const title = el.shadowRoot.querySelector(".card h2");
      expect(title).to.not.be.null;
      expect(title.textContent.trim().length).to.be.greaterThan(0);
    });
  });

  // ------------------------------------------------------------------
  // Prices tab
  // ------------------------------------------------------------------

  describe("prices tab", () => {
    it("renders price form elements", async () => {
      const el = await createPanel();

      // Switch to prices tab (index 2)
      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[2].click();
      await el.updateComplete;

      const priceInput = el.shadowRoot.querySelector("#price-value");
      expect(priceInput).to.not.be.null;
      expect(priceInput.getAttribute("type")).to.equal("number");

      const validFromInput = el.shadowRoot.querySelector("#price-from");
      expect(validFromInput).to.not.be.null;
    });

    it("shows 'no prices' message when no prices exist", async () => {
      const el = await createPanel();

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[2].click();
      await el.updateComplete;

      const text = el.shadowRoot.textContent;
      // German: "Noch keine Preise erfasst."
      expect(text).to.include("keine Preise");
    });

    it("renders price save button", async () => {
      const el = await createPanel();

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[2].click();
      await el.updateComplete;

      const saveBtn = el.shadowRoot.querySelector("button.primary");
      expect(saveBtn).to.not.be.null;
    });

    it("shows gas conversion factors for gas meters", async () => {
      const el = await createPanel();

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[2].click();
      await el.updateComplete;

      // Gas meters should show the conversion factor form
      const gasParamsSection = el.shadowRoot.querySelector("#calorific-value");
      expect(gasParamsSection).to.not.be.null;
    });

    it("hides gas conversion factors for water meters", async () => {
      const waterMeter = {
        ...MOCK_METER,
        meter_type: "water",
        meter_name: "Wasserzähler",
      };
      const el = await createPanel({ meters: [waterMeter] });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[2].click();
      await el.updateComplete;

      const gasParams = el.shadowRoot.querySelector("#calorific-value");
      expect(gasParams).to.be.null;
    });
  });

  // ------------------------------------------------------------------
  // Chart tab
  // ------------------------------------------------------------------

  describe("chart tab", () => {
    it("shows minimum readings message when there are no readings", async () => {
      const el = await createPanel();

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[3].click();
      await el.updateComplete;

      const text = el.shadowRoot.textContent;
      // "Mindestens 2 Ablesungen" or English equivalent
      expect(
        text.includes("Mindestens 2") || text.includes("At least 2")
      ).to.be.true;
    });

    it("renders a canvas element when there are enough statistics", async () => {
      const mockStats = [
        { timestamp: "2025-01-01T10:00:00Z", reading: 100.0, consumption: null, days: 0, meter_number: "GAS-001" },
        { timestamp: "2025-02-01T10:00:00Z", reading: 105.5, consumption: 5.5, days: 31, meter_number: "GAS-001" },
        { timestamp: "2025-03-01T10:00:00Z", reading: 112.0, consumption: 6.5, days: 28, meter_number: "GAS-001" },
      ];
      const el = await createPanel({ readings: MOCK_READINGS, statistics: mockStats });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[3].click();
      await el.updateComplete;

      // Give Chart.js time to render
      await new Promise((r) => setTimeout(r, 100));
      await el.updateComplete;

      const canvas = el.shadowRoot.querySelector("canvas");
      expect(canvas).to.not.be.null;
    });
  });

  // ------------------------------------------------------------------
  // Empty history state
  // ------------------------------------------------------------------

  describe("empty history state", () => {
    it("shows 'no readings' message when history is empty", async () => {
      const el = await createPanel();

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const text = el.shadowRoot.textContent;
      // "Noch keine Ablesungen vorhanden."
      expect(text).to.include("keine Ablesungen");
    });
  });

  // ------------------------------------------------------------------
  // OCR upload feedback messages
  // ------------------------------------------------------------------

  describe("OCR upload feedback", () => {
    it("shows success hint when ocr_reading is present", async () => {
      const el = await createPanel();
      // Simulate a successful OCR upload result
      el._uploadResult = {
        image_path: "/media/test.jpg",
        ocr_available: true,
        ocr_reading: 12345.678,
        ocr_confidence: 0.95,
        ocr_meter_number: "GAS-001",
        exif_datetime: null,
      };
      await el.updateComplete;

      const hint = el.shadowRoot.querySelector(".ocr-hint.ocr-success");
      expect(hint).to.not.be.null;
      expect(hint.textContent).to.include("12345.678");
      expect(hint.textContent).to.include("95%");
    });

    it("shows warning when ocr_available is false", async () => {
      const el = await createPanel();
      el._uploadResult = {
        image_path: "/media/test.jpg",
        ocr_available: false,
        ocr_reading: null,
        ocr_confidence: 0.0,
        ocr_meter_number: null,
        exif_datetime: null,
      };
      await el.updateComplete;

      const hint = el.shadowRoot.querySelector(".ocr-hint.ocr-warn");
      expect(hint).to.not.be.null;
      // German: "nicht installiert" / English: "not installed"
      expect(hint.textContent).to.include("nicht installiert");
    });

    it("shows no-result warning when ocr_available is true but no reading", async () => {
      const el = await createPanel();
      el._uploadResult = {
        image_path: "/media/test.jpg",
        ocr_available: true,
        ocr_reading: null,
        ocr_confidence: 0.0,
        ocr_meter_number: null,
        exif_datetime: null,
      };
      await el.updateComplete;

      const hint = el.shadowRoot.querySelector(".ocr-hint.ocr-warn");
      expect(hint).to.not.be.null;
      // German: "nicht automatisch erkannt" / English: "could not be detected"
      expect(hint.textContent).to.include("nicht automatisch erkannt");
    });

    it("does not show any OCR hint when no upload result exists", async () => {
      const el = await createPanel();
      // _uploadResult is null by default
      expect(el._uploadResult).to.be.null;
      await el.updateComplete;

      const hints = el.shadowRoot.querySelectorAll(".ocr-hint");
      expect(hints.length).to.equal(0);
    });

    it("pre-fills reading input with OCR value when available", async () => {
      const el = await createPanel();
      el._uploadResult = {
        image_path: "/media/test.jpg",
        ocr_available: true,
        ocr_reading: 42.5,
        ocr_confidence: 0.88,
        ocr_meter_number: "W-007",
        exif_datetime: null,
      };
      await el.updateComplete;

      const readingInput = el.shadowRoot.getElementById("reading-value");
      expect(readingInput).to.not.be.null;
      expect(parseFloat(readingInput.value)).to.equal(42.5);
    });
  });

  // ------------------------------------------------------------------
  // Desktop action buttons icon visibility
  // ------------------------------------------------------------------

  describe("desktop action icon visibility", () => {
    it("icon buttons have ha-icon elements with explicit icon property", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      const iconBtns = el.shadowRoot.querySelectorAll(".icon-btn");
      // 2 rows * 3 buttons each = 6
      expect(iconBtns.length).to.equal(6);

      for (const btn of iconBtns) {
        const icon = btn.querySelector("ha-icon");
        expect(icon).to.not.be.null;
        expect(icon.icon).to.be.a("string").that.is.not.empty;
      }
    });

    it("ha-icon has default display style for visibility", async () => {
      const el = await createPanel({ narrow: false, readings: MOCK_READINGS });

      const tabs = el.shadowRoot.querySelectorAll(".tab");
      tabs[1].click();
      await el.updateComplete;

      // Check that the ha-icon inside an icon-btn is visible (not display:none)
      const firstIcon = el.shadowRoot.querySelector(".icon-btn ha-icon");
      expect(firstIcon).to.not.be.null;
      const style = window.getComputedStyle(firstIcon);
      expect(style.display).to.not.equal("none");
    });
  });
});

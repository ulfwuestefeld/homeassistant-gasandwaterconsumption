import { fixture, expect, html } from "@open-wc/testing";
import { setViewport } from "@web/test-runner-commands";

// Stub Home Assistant custom elements that are not available outside HA.
if (!customElements.get("ha-icon")) {
  customElements.define(
    "ha-icon",
    class HaIconStub extends HTMLElement {
      static get observedAttributes() {
        return ["icon"];
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

function createMockHass(lang = "de") {
  return {
    language: lang,
    connection: {
      sendMessagePromise: async (msg) => {
        switch (msg.type) {
          case "gas_water_meter/list_meters":
            return { meters: [MOCK_METER] };
          case "gas_water_meter/get_readings":
            return { readings: [] };
          case "gas_water_meter/get_prices":
            return { prices: [] };
          case "gas_water_meter/get_statistics":
            return { statistics: [] };
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

async function createPanel({ narrow = false, lang = "de" } = {}) {
  const hass = createMockHass(lang);

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
    it("shows the hamburger menu when narrow is true", async () => {
      const el = await createPanel({ narrow: true });
      const menuBtn = el.shadowRoot.querySelector(".menu-btn");

      expect(menuBtn).to.not.be.null;
      const icon = menuBtn.querySelector("ha-icon");
      expect(icon).to.not.be.null;
      expect(icon.getAttribute("icon")).to.equal("mdi:menu");
    });

    it("hides the hamburger menu when narrow is false", async () => {
      const el = await createPanel({ narrow: false });
      const menuBtn = el.shadowRoot.querySelector(".menu-btn");

      expect(menuBtn).to.be.null;
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

    it("toggles narrow dynamically", async () => {
      const el = await createPanel({ narrow: false });
      expect(el.shadowRoot.querySelector(".menu-btn")).to.be.null;

      // Switch to narrow
      el.narrow = true;
      await el.updateComplete;
      expect(el.shadowRoot.querySelector(".menu-btn")).to.not.be.null;

      // Switch back
      el.narrow = false;
      await el.updateComplete;
      expect(el.shadowRoot.querySelector(".menu-btn")).to.be.null;
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
  });
});

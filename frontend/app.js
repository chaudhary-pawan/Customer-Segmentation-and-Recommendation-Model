// =============================================
// API ENDPOINTS (same as before, no changes)
// =============================================
const API = {
  existingCustomer: "/api/recommend-existing",
  newCustomer: "/api/recommend-new",
  downloadCsv: "/api/download-recommendations",
};

// =============================================
// FIELD DEFINITIONS
// =============================================
const demoFields = [
  { name: "Education", hint: "0=Basic 1=Grad 2=Master 3=PhD 4=2n Cycle" },
  { name: "Income", hint: "Annual income (e.g. 52000)" },
  { name: "Kidhome", hint: "Young kids at home (0, 1, 2)" },
  { name: "Teenhome", hint: "Teens at home (0, 1, 2)" },
  { name: "Age", hint: "Age in years (e.g. 40)" },
  { name: "Living_With", hint: "1 = Alone   2 = With Partner" },
  { name: "Customer_For", hint: "Days since enrollment (e.g. 365)" },
];
const spendFields = [
  { name: "Wines", hint: "e.g. 200" },
  { name: "Fruits", hint: "e.g. 50" },
  { name: "Meat", hint: "e.g. 120" },
  { name: "Fish", hint: "e.g. 30" },
  { name: "Sweets", hint: "e.g. 20" },
  { name: "Gold", hint: "e.g. 40" },
];
const behaviourFields = [
  { name: "Recency", hint: "Days since last purchase" },
  { name: "NumDealsPurchases", hint: "Purchases via discount" },
  { name: "NumWebPurchases", hint: "Purchases via website" },
  { name: "NumCatalogPurchases", hint: "Purchases via catalogue" },
  { name: "NumStorePurchases", hint: "Purchases in-store" },
  { name: "NumWebVisitsMonth", hint: "Website visits/month" },
];

// =============================================
// PRODUCT STYLING MAP
// =============================================
const PRODUCT_META = {
  Wines: { emoji: "🍷", cls: "cp-wines" },
  Fruits: { emoji: "🍎", cls: "cp-fruits" },
  Meat: { emoji: "🥩", cls: "cp-meat" },
  Fish: { emoji: "🐟", cls: "cp-fish" },
  Sweets: { emoji: "🍬", cls: "cp-sweets" },
  Gold: { emoji: "🥇", cls: "cp-gold" },
};

const SIM_META = {
  "Very High": { color: "sc-vh", badge: "sb-vh", fill: "sf-vh" },
  "High": { color: "sc-h", badge: "sb-h", fill: "sf-h" },
  "Moderate": { color: "sc-m", badge: "sb-m", fill: "sf-m" },
  "Low": { color: "sc-l", badge: "sb-l", fill: "sf-l" },
  "Very Low": { color: "sc-vl", badge: "sb-vl", fill: "sf-vl" },
};

// =============================================
// BUILD FORM FIELDS DYNAMICALLY
// =============================================
function buildFields(containerId, fields) {
  const container = document.getElementById(containerId);
  if (!container) return;
  fields.forEach(({ name, hint }) => {
    const div = document.createElement("div");
    div.className = "fitem";
    div.innerHTML = `
      <label title="${name}">${name.replace(/_/g, " ")}</label>
      <input type="number" step="any" data-field="${name}" placeholder="${hint}" />
    `;
    container.appendChild(div);
  });
}

buildFields("demo-fields", demoFields);
buildFields("spend-fields", spendFields);
buildFields("behaviour-fields", behaviourFields);

// =============================================
// LIVE AUTO-DERIVED PREVIEW
// =============================================
function get(name) {
  const el = document.querySelector(`[data-field="${name}"]`);
  return el ? (parseFloat(el.value) || 0) : 0;
}

function updateAutoPreview() {
  const kidhome = get("Kidhome");
  const teenhome = get("Teenhome");
  const livingWith = Math.min(get("Living_With") || 1, 2);
  const spent = get("Wines") + get("Fruits") + get("Meat") + get("Fish") + get("Sweets") + get("Gold");
  const children = kidhome + teenhome;
  const isParent = children > 0 ? 1 : 0;
  const familySize = kidhome + teenhome + 1 + (livingWith >= 2 ? 1 : 0);

  const $ = (id) => document.getElementById(id);
  $("p-spent").textContent = spent;
  $("p-children").textContent = children;
  $("p-family").textContent = familySize;
  $("p-parent").textContent = isParent ? "Yes" : "No";
}
document.addEventListener("input", e => {
  if (e.target.dataset.field) updateAutoPreview();
});
updateAutoPreview();

// =============================================
// RESULT RENDERING
// =============================================
function renderResult(data, contentId, panelId, isNew) {
  const panel = document.getElementById(panelId);
  const content = document.getElementById(contentId);

  const sim = data.similarity_score || 0;
  const level = data.similarity_level || "Low";
  const meta = SIM_META[level] || SIM_META["Low"];
  const pct = Math.min(Math.round(sim * 100), 100);
  const products = data.recommended_products || [];
  const derived = data.auto_derived_fields || null;

  const productChips = products.length
    ? products.map(p => {
      const m = PRODUCT_META[p] || { emoji: "📦", cls: "cp-def" };
      return `<span class="chip ${m.cls}">${m.emoji} ${p}</span>`;
    }).join("")
    : `<span style="color:#6b7280;font-size:.82rem">No uplift products found.</span>`;

  const derivedHtml = derived
    ? `<div class="der-grid">${Object.entries(derived).map(([k, v]) => `
          <div class="der-item">
            <div class="der-k">${k.replace(/_/g, " ")}</div>
            <div class="der-v">${v}</div>
          </div>`).join("")
    }</div>` : "";

  const warnHtml = data.warning
    ? `<div class="warn">⚠️ <span>${data.warning}</span></div>` : "";

  const barId = `bar-${panelId}`;

  content.innerHTML = `
    <div class="rcard">
      <div class="rcard-hdr">
        <span class="cbadge">Cluster ${data.cluster}</span>
        <span style="font-size:.82rem;color:#6b7280">${isNew ? "New Customer" : "Customer #" + data.customer_index}</span>
      </div>
      <div class="rcard-body">
        <div>
          <div class="sim-row">
            <span class="sim-lbl">Similarity to Cluster</span>
            <span class="sim-val ${meta.color}">${sim.toFixed(4)}</span>
          </div>
          <div class="sim-track">
            <div class="sim-fill ${meta.fill}" id="${barId}" style="width:0%"></div>
          </div>
          <span class="slbadge ${meta.badge}">${level}</span>
        </div>
        <div class="prod-title">Recommended Products</div>
        <div class="chips">${productChips}</div>
        ${derivedHtml}
        ${warnHtml}
      </div>
    </div>
  `;

  panel.style.display = "block";
  requestAnimationFrame(() => {
    setTimeout(() => {
      const bar = document.getElementById(barId);
      if (bar) bar.style.width = pct + "%";
    }, 50);
  });
}

// =============================================
// LOADER
// =============================================
const showLoader = () => document.getElementById("loader").style.display = "flex";
const hideLoader = () => document.getElementById("loader").style.display = "none";

// =============================================
// TAB NAVIGATION
// =============================================
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("panel-" + tab).classList.add("active");
  });
});

// =============================================
// EXISTING CUSTOMER
// =============================================
document.getElementById("btn-existing").addEventListener("click", async () => {
  const idx = parseInt(document.getElementById("existing-index").value, 10);
  if (isNaN(idx) || idx < 0) {
    alert("Please enter a valid customer index (0 or above).");
    return;
  }
  showLoader();
  try {
    const res = await fetch(API.existingCustomer, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_index: idx }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || `HTTP ${res.status}`); }
    renderResult(await res.json(), "existing-result-content", "existing-result-panel", false);
  } catch (err) {
    document.getElementById("existing-result-panel").style.display = "block";
    document.getElementById("existing-result-content").innerHTML =
      `<div class="rcard"><div class="rcard-body"><div class="warn">❌ <span>${err.message}</span></div></div></div>`;
  } finally { hideLoader(); }
});

// =============================================
// NEW CUSTOMER
// =============================================
document.getElementById("btn-new").addEventListener("click", async () => {
  const payload = {};
  const allFields = [...demoFields, ...spendFields, ...behaviourFields];
  let hasError = false;

  allFields.forEach(({ name }) => {
    const input = document.querySelector(`[data-field="${name}"]`);
    if (!input || input.value === "") {
      hasError = true;
      if (input) input.style.borderColor = "#ef4444";
    } else {
      payload[name] = Number(input.value);
      input.style.borderColor = "";
    }
  });

  if (hasError) { alert("Please fill in all fields."); return; }

  showLoader();
  try {
    const res = await fetch(API.newCustomer, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || `HTTP ${res.status}`); }
    renderResult(await res.json(), "new-result-content", "new-result-panel", true);
  } catch (err) {
    document.getElementById("new-result-panel").style.display = "block";
    document.getElementById("new-result-content").innerHTML =
      `<div class="rcard"><div class="rcard-body"><div class="warn">❌ <span>${err.message}</span></div></div></div>`;
  } finally { hideLoader(); }
});

// =============================================
// CSV TABLE
// =============================================
document.getElementById("btn-load-csv").addEventListener("click", async () => {
  showLoader();
  try {
    const res = await fetch(API.downloadCsv);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const rows = await res.json();

    if (!rows || rows.length === 0) {
      document.getElementById("csv-empty").innerHTML = "<p>No records found.</p>";
      return;
    }
    const cols = Object.keys(rows[0]);
    document.getElementById("csv-head").innerHTML =
      `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;
    document.getElementById("csv-body").innerHTML =
      rows.map(r => `<tr>${cols.map(c => `<td>${r[c] ?? "—"}</td>`).join("")}</tr>`).join("");

    document.getElementById("csv-wrapper").style.display = "block";
    document.getElementById("csv-empty").style.display = "none";
  } catch (err) {
    document.getElementById("csv-empty").innerHTML =
      `<p style="color:#f87171">Failed: ${err.message}</p>`;
  } finally { hideLoader(); }
});
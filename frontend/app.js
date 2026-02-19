// API base — all endpoints are now under /api
const API_BASE = "";  // same origin, use relative paths

const fieldMeta = [
  { name: "Education", hint: "Categorical/ordinal code (e.g., 0–4)" },
  { name: "Income", hint: "Annual income (e.g., 50000)" },
  { name: "Kidhome", hint: "Number of kids at home (0/1/2…)" },
  { name: "Teenhome", hint: "Number of teens at home (0/1/2…)" },
  { name: "Recency", hint: "Days since last purchase (e.g., 10)" },
  { name: "Wines", hint: "Spend on wines (e.g., 200)" },
  { name: "Fruits", hint: "Spend on fruits (e.g., 50)" },
  { name: "Meat", hint: "Spend on meat (e.g., 120)" },
  { name: "Fish", hint: "Spend on fish (e.g., 30)" },
  { name: "Sweets", hint: "Spend on sweets (e.g., 20)" },
  { name: "Gold", hint: "Spend on gold products (e.g., 10)" },
  { name: "NumDealsPurchases", hint: "Number of deals purchases (e.g., 2)" },
  { name: "NumWebPurchases", hint: "Number of web purchases (e.g., 3)" },
  { name: "NumCatalogPurchases", hint: "Number of catalog purchases (e.g., 1)" },
  { name: "NumStorePurchases", hint: "Number of store purchases (e.g., 4)" },
  { name: "NumWebVisitsMonth", hint: "Web visits per month (e.g., 5)" },
  { name: "Customer_For", hint: "Days as customer (e.g., 200)" },
  { name: "Age", hint: "Age in years (e.g., 40)" },
  { name: "Spent", hint: "Total spend (e.g., 430)" },
  { name: "Living_With", hint: "Household type code (e.g., 1)" },
  { name: "Children", hint: "Total children count (e.g., 0/1/2)" },
  { name: "Family_Size", hint: "Household size (e.g., 2/3/4)" },
  { name: "Is_Parent", hint: "Parent flag (0/1)" },
];

// Build dynamic form with hints
const formContainer = document.getElementById("new-customer-form");
fieldMeta.forEach(({ name, hint }) => {
  const div = document.createElement("div");
  div.className = "col-12";
  div.innerHTML = `
    <label class="form-label small">${name}</label>
    <input type="number" step="any" class="form-control form-control-sm"
      data-field="${name}" placeholder="${hint}" />
  `;
  formContainer.appendChild(div);
});

const existingResultEl = document.getElementById("existing-result");
const newResultEl = document.getElementById("new-result");

document.getElementById("btn-existing").onclick = async () => {
  const idx = parseInt(document.getElementById("existing-index").value, 10);
  if (Number.isNaN(idx)) {
    existingResultEl.textContent = "Enter a valid index";
    return;
  }
  existingResultEl.textContent = "Loading...";
  try {
    const res = await fetch(`/api/recommend-existing`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_index: idx }),
    });
    const data = await res.json();
    existingResultEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    existingResultEl.textContent = `Error: ${err}`;
  }
};

document.getElementById("btn-new").onclick = async () => {
  const payload = {};
  document.querySelectorAll("[data-field]").forEach((input) => {
    const val = input.value;
    payload[input.dataset.field] = val === "" ? null : Number(val);
  });
  newResultEl.textContent = "Loading...";
  try {
    const res = await fetch(`/api/recommend-new`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    newResultEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    newResultEl.textContent = `Error: ${err}`;
  }
};

document.getElementById("btn-load-csv").onclick = async () => {
  const headEl = document.getElementById("csv-head");
  const bodyEl = document.getElementById("csv-body");
  headEl.innerHTML = "";
  bodyEl.innerHTML = "";
  try {
    const res = await fetch(`/api/download-recommendations`);
    const rows = await res.json();
    if (!rows || rows.length === 0) {
      headEl.innerHTML = "<tr><th>No data</th></tr>";
      return;
    }
    const cols = Object.keys(rows[0]);
    headEl.innerHTML = `<tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr>`;
    bodyEl.innerHTML = rows
      .map(
        (r) =>
          `<tr>${cols
            .map((c) => `<td>${r[c] !== undefined ? r[c] : ""}</td>`)
            .join("")}</tr>`
      )
      .join("");
  } catch (err) {
    headEl.innerHTML = "<tr><th>Error loading data</th></tr>";
  }
};
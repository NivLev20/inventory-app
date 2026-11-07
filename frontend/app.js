/* Smart Retail Inventory dashboard.
 * Talks to the Flask API through the same origin: nginx forwards /api/* to the backend.
 */
"use strict";

const API = "/api";
let trendChart = null;
let restockChart = null;
let allProducts = [];
let restockTarget = null;

const $ = (id) => document.getElementById(id);
const fmtNumber = (n) => Number(n).toLocaleString("en-US");
const fmtMoney = (n) => "₪" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
  })[c]);
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return body;
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2500);
}

// ---------------------------------------------------------------- render

function renderKpis(data) {
  $("kpi-products").textContent = fmtNumber(data.total_products);
  $("kpi-units").textContent = fmtNumber(data.total_units);
  $("kpi-value").textContent = fmtMoney(data.inventory_value);
  $("kpi-alerts").textContent = fmtNumber(data.by_status.LOW + data.by_status.OUT);
}

function chartColors() {
  const css = getComputedStyle(document.documentElement);
  return {
    brand: css.getPropertyValue("--brand").trim(),
    muted: css.getPropertyValue("--muted").trim(),
    line: css.getPropertyValue("--line").trim()
  };
}

function renderCharts(data) {
  if (typeof Chart === "undefined") return; // chart library blocked/offline: the rest still works
  const c = chartColors();
  const labels = data.stock_trend.map((d) => d.date.slice(5));
  const common = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: c.muted }, grid: { display: false } },
      y: { ticks: { color: c.muted }, grid: { color: c.line }, beginAtZero: true }
    }
  };

  if (trendChart) trendChart.destroy();
  trendChart = new Chart($("chart-trend"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        data: data.stock_trend.map((d) => d.total_units),
        borderColor: c.brand,
        backgroundColor: c.brand + "22",
        fill: true,
        tension: 0.3,
        pointRadius: 2
      }]
    },
    options: common
  });

  if (restockChart) restockChart.destroy();
  restockChart = new Chart($("chart-restocks"), {
    type: "bar",
    data: {
      labels,
      datasets: [{ data: data.restocks_trend.map((d) => d.units), backgroundColor: c.brand, borderRadius: 4 }]
    },
    options: common
  });
}

function renderLowStock(items) {
  const box = $("low-list");
  if (!items.length) {
    box.innerHTML = "<p class=\"empty\">All products are above their minimum level. 🎉</p>";
    return;
  }
  box.innerHTML = items.map((p) => `
    <div class="low-item ${p.status}">
      <strong>${escapeHtml(p.name)}</strong>
      <span class="meta">${escapeHtml(p.store)} · ${p.stock} left (min ${p.min_stock})</span>
      <button class="btn small primary" data-quick="${p.id}" data-qty="${p.suggested_reorder}">
        Order ${p.suggested_reorder}
      </button>
    </div>`).join("");
}

function renderProducts() {
  const store = $("filter-store").value;
  const status = $("filter-status").value;
  const rows = allProducts.filter((p) => (!store || p.store === store) && (!status || p.status === status));
  $("products-body").innerHTML = rows.map((p) => `
    <tr>
      <td>${escapeHtml(p.name)}</td>
      <td>${escapeHtml(p.sku)}</td>
      <td>${escapeHtml(p.store)}</td>
      <td>${escapeHtml(p.category)}</td>
      <td class="num">${fmtNumber(p.stock)}</td>
      <td class="num">${fmtNumber(p.min_stock)}</td>
      <td><span class="pill ${p.status}">${p.status}</span></td>
      <td>
        <button class="btn small" data-restock="${p.id}">Restock</button>
        <button class="btn small danger" data-delete="${p.id}" aria-label="Delete ${escapeHtml(p.name)}">✕</button>
      </td>
    </tr>`).join("") || "<tr><td colspan=\"8\" class=\"empty\">No products match the filter.</td></tr>";
}

function renderStoreFilter() {
  const select = $("filter-store");
  const current = select.value;
  const stores = [...new Set(allProducts.map((p) => p.store))].sort();
  select.innerHTML = "<option value=\"\">All stores</option>" +
    stores.map((s) => `<option${s === current ? " selected" : ""}>${escapeHtml(s)}</option>`).join("");
}

function renderRestocks(logs) {
  $("restock-list").innerHTML = logs.slice(0, 8).map((r) => `
    <li>
      <span>+${r.quantity} × ${escapeHtml(r.product_name)} <span class="when">(${escapeHtml(r.store)})</span></span>
      <span class="when">${r.created_at.replace("T", " ").slice(0, 16)}</span>
    </li>`).join("") || "<li class=\"empty\">No restocks yet.</li>";
}

// ---------------------------------------------------------------- data

async function loadAll() {
  try {
    const [analytics, products, low, restocks] = await Promise.all([
      api("/products/analytics"),
      api("/products"),
      api("/products/low-stock"),
      api("/restocks")
    ]);
    allProducts = products;
    renderKpis(analytics);
    renderCharts(analytics);
    renderLowStock(low);
    renderStoreFilter();
    renderProducts();
    renderRestocks(restocks);
    setApiStatus(true);
  } catch (err) {
    setApiStatus(false);
    toast("Could not load data: " + err.message);
  }
}

function setApiStatus(up) {
  const el = $("api-status");
  el.textContent = up ? "API online" : "API offline";
  el.className = "api-status " + (up ? "up" : "down");
}

async function restock(productId, quantity, note) {
  const product = await api(`/products/${productId}/restock`, {
    method: "POST",
    body: JSON.stringify({ quantity, note })
  });
  toast(`${product.name}: stock is now ${product.stock}`);
  await loadAll();
}

// ---------------------------------------------------------------- events

document.addEventListener("click", async (event) => {
  const t = event.target;

  if (t.matches("[data-close]")) {
    t.closest("dialog").close();
  } else if (t.dataset.quick) {
    await restock(t.dataset.quick, Number(t.dataset.qty), "suggested reorder")
      .catch((err) => toast(err.message));
  } else if (t.dataset.restock) {
    restockTarget = allProducts.find((p) => String(p.id) === t.dataset.restock);
    $("restock-name").textContent = restockTarget.name;
    $("restock-error").textContent = "";
    $("form-restock").reset();
    $("dlg-restock").showModal();
  } else if (t.dataset.delete) {
    const product = allProducts.find((p) => String(p.id) === t.dataset.delete);
    if (window.confirm(`Delete "${product.name}"?`)) {
      try {
        await api(`/products/${product.id}`, { method: "DELETE" });
        toast("Product deleted");
        await loadAll();
      } catch (err) {
        toast(err.message);
      }
    }
  }
});

$("btn-add").addEventListener("click", () => {
  $("add-error").textContent = "";
  $("dlg-add").showModal();
});

$("form-add").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = Object.fromEntries(form.entries());
  ["stock", "min_stock", "price"].forEach((k) => { payload[k] = Number(payload[k]); });
  try {
    await api("/products", { method: "POST", body: JSON.stringify(payload) });
    $("dlg-add").close();
    event.target.reset();
    toast("Product added");
    await loadAll();
  } catch (err) {
    $("add-error").textContent = err.message;
  }
});

$("form-restock").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    await restock(restockTarget.id, Number(form.get("quantity")), form.get("note"));
    $("dlg-restock").close();
  } catch (err) {
    $("restock-error").textContent = err.message;
  }
});

$("filter-store").addEventListener("change", renderProducts);
$("filter-status").addEventListener("change", renderProducts);

loadAll();
setInterval(loadAll, 30000); // refresh every 30 seconds

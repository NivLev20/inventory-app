// Same-origin "/api" calls; nginx (production) or Vite (development) proxies them to the backend.

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return body;
}

export const api = {
  getProducts: () => request("/products"),
  getLowStock: () => request("/products/low-stock"),
  getAnalytics: () => request("/products/analytics"),
  getRestocks: () => request("/restocks"),
  addProduct: (product) => request("/products", { method: "POST", body: JSON.stringify(product) }),
  deleteProduct: (id) => request(`/products/${id}`, { method: "DELETE" }),
  restock: (id, quantity, note) =>
    request(`/products/${id}/restock`, { method: "POST", body: JSON.stringify({ quantity, note }) }),
  getSimulation: () => request("/simulation"),
  setSimulation: (enabled) => request("/simulation", { method: "PUT", body: JSON.stringify({ enabled }) }),
  rushHour: () => request("/simulation/rush", { method: "POST" })
};

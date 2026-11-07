// Product table with filters by store and status.
// The filter values are local state: only this component needs them.
import { useState } from "react";
import { fmtNumber } from "../format.js";

export default function ProductsTable({ products, onRestock, onDelete }) {
  const [store, setStore] = useState("");
  const [status, setStatus] = useState("");

  // Build the store list from the data itself (no hard-coded store names)
  const stores = [...new Set(products.map((p) => p.store))].sort();
  const rows = products.filter(
    (p) => (!store || p.store === store) && (!status || p.status === status)
  );

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>All products</h2>
        <div className="filters">
          <select aria-label="Filter by store" value={store} onChange={(e) => setStore(e.target.value)}>
            <option value="">All stores</option>
            {stores.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="OK">OK</option>
            <option value="LOW">Low</option>
            <option value="OUT">Out of stock</option>
          </select>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Product</th><th>SKU</th><th>Store</th><th>Category</th>
              <th className="num">Stock</th><th className="num">Min</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan="8" className="empty">No products match the filter.</td></tr>
            )}
            {rows.map((p) => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td className="sku">{p.sku}</td>
                <td>{p.store}</td>
                <td>{p.category}</td>
                <td className="num">{fmtNumber(p.stock)}</td>
                <td className="num">{fmtNumber(p.min_stock)}</td>
                <td><span className={`pill ${p.status}`}>{p.status}</span></td>
                <td>
                  <div className="row-actions">
                    <button className="btn small" onClick={() => onRestock(p)}>Restock</button>
                    <button
                      className="btn small danger"
                      aria-label={`Delete ${p.name}`}
                      onClick={() => onDelete(p)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

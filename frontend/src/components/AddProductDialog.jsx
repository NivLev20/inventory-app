import { useState } from "react";
import Modal from "./Modal.jsx";

const EMPTY = { name: "", sku: "", store: "Tel Aviv", category: "General", stock: 0, min_stock: 10, price: 0 };

export default function AddProductDialog({ onSave, onClose }) {
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function update(e) {
    const { name, value, type } = e.target;
    setForm({ ...form, [name]: type === "number" ? Number(value) : value });
  }

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(form);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Add product" onClose={onClose}>
      <form onSubmit={submit}>
        <label>Name <input name="name" value={form.name} onChange={update} required /></label>
        <label>SKU <input name="sku" value={form.sku} onChange={update} required /></label>
        <div className="row">
          <label>Store <input name="store" value={form.store} onChange={update} /></label>
          <label>Category <input name="category" value={form.category} onChange={update} /></label>
        </div>
        <div className="row">
          <label>Stock <input name="stock" type="number" min="0" value={form.stock} onChange={update} /></label>
          <label>Min stock <input name="min_stock" type="number" min="0" value={form.min_stock} onChange={update} /></label>
          <label>Price <input name="price" type="number" min="0" step="0.01" value={form.price} onChange={update} /></label>
        </div>
        <p className="form-error">{error}</p>
        <div className="dlg-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn primary" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

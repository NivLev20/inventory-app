// "Restock" form for one product: quantity + optional note.
import { useState } from "react";
import Modal from "./Modal.jsx";

export default function RestockDialog({ product, onSave, onClose }) {
  const [quantity, setQuantity] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(Number(quantity), note);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={`Restock ${product.name}`} onClose={onClose}>
      <form onSubmit={submit}>
        <p className="muted">Current stock: {product.stock} (minimum {product.min_stock})</p>
        <label>
          Quantity
          <input type="number" min="1" required autoFocus value={quantity}
                 onChange={(e) => setQuantity(e.target.value)} />
        </label>
        <label>
          Note
          <input placeholder="e.g. supplier order #123" value={note}
                 onChange={(e) => setNote(e.target.value)} />
        </label>
        <p className="form-error">{error}</p>
        <div className="dlg-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn primary" disabled={saving}>
            {saving ? "Saving…" : "Restock"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

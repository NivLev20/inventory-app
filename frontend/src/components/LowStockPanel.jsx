// "Needs restocking" panel: one card per LOW / OUT product with a one-click Order button.
// Props: items (low-stock products from the API), onOrder(product)
export default function LowStockPanel({ items, onOrder }) {
  return (
    <section className="card">
      <h2>⚠ Needs restocking</h2>
      {items.length === 0 ? (
        <p className="empty">All products are above their minimum level. 🎉</p>
      ) : (
        <div className="low-list">
          {items.map((p) => (
            // "key" helps React track which card is which when the list changes
            <div key={p.id} className={`low-item ${p.status}`}>
              <strong>{p.name}</strong>
              <span className="meta">
                {p.store} · {p.stock} left (min {p.min_stock})
              </span>
              <button className="btn small primary" onClick={() => onOrder(p)}>
                Order {p.suggested_reorder}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

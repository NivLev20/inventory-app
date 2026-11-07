// Products at or below their minimum, drawn as shelf-edge labels.
export default function LowStockPanel({ items, onOrder }) {
  return (
    <section className="shelf">
      <div className="panel-head">
        <h2>Needs restocking</h2>
        <span className="muted">{items.length ? `${items.length} products` : ""}</span>
      </div>
      {items.length === 0 ? (
        <p className="empty">Every product is above its minimum level.</p>
      ) : (
        <div className="shelf-rail">
          {items.map((p) => (
            <article key={p.id} className={`tag ${p.status}`}>
              <span className="tag-name">{p.name}</span>
              <span className="tag-store">{p.store}</span>
              <span className="tag-count">
                {p.stock} <small>left, minimum {p.min_stock}</small>
              </span>
              <span className="tag-sku">{p.sku}</span>
              <button className="btn small" onClick={() => onOrder(p)}>
                Order {p.suggested_reorder}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

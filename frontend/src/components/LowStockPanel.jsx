// Gauge scale runs to the reorder target (2 x minimum); the marker at 50% is the minimum.
export default function LowStockPanel({ items, onOrder }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Needs restocking</h2>
        {items.length > 0 && <span className="muted">{items.length} products</span>}
      </div>
      {items.length === 0 ? (
        <p className="empty">Every product is above its minimum level.</p>
      ) : (
        <div className="restock-list">
          {items.map((p) => {
            const target = Math.max(p.min_stock * 2, 1);
            const fill = Math.min(100, (p.stock / target) * 100);
            return (
              <article key={p.id} className={`restock-item ${p.status}`}>
                <div className="restock-top">
                  <div>
                    <div className="restock-name">{p.name}</div>
                    <div className="restock-store">{p.store}</div>
                  </div>
                  <span className="restock-count">{p.stock}</span>
                </div>
                <div className="gauge" role="img" aria-label={`${p.stock} in stock, minimum ${p.min_stock}`}>
                  <span className="gauge-fill" style={{ width: `${fill}%` }} />
                  <span className="gauge-min" style={{ left: "50%" }} />
                </div>
                <div className="restock-foot">
                  <span className="restock-meta">Minimum {p.min_stock}, {p.sku}</span>
                  {p.suggested_reorder > 0 && (
                    <button className="btn small primary" onClick={() => onOrder(p)}>
                      Order {p.suggested_reorder}
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

// The 8 most recent restocks.
import { fmtDateTime } from "../format.js";

export default function RestockHistory({ restocks }) {
  const recent = restocks.slice(0, 8);
  return (
    <section className="card">
      <h2>Recent restocks</h2>
      <ul className="restock-list">
        {recent.length === 0 && <li className="empty">No restocks yet.</li>}
        {recent.map((r) => (
          <li key={r.id}>
            <span>
              +{r.quantity} × {r.product_name} <span className="when">({r.store})</span>
            </span>
            <span className="when">{fmtDateTime(r.created_at)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

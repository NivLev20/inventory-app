import { fmtDateTime } from "../format.js";

export default function RestockHistory({ restocks }) {
  const recent = restocks.slice(0, 7);
  return (
    <section className="panel">
      <div className="panel-head"><h2>Recent deliveries</h2></div>
      {recent.length === 0 ? (
        <p className="empty">No deliveries yet.</p>
      ) : (
        <ul className="activity">
          {recent.map((r) => (
            <li key={r.id}>
              <span className="what">
                <span className="qty">+{r.quantity}</span>
                {r.product_name} <span className="where">{r.store}</span>
              </span>
              <span className="when">{fmtDateTime(r.created_at).slice(5)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

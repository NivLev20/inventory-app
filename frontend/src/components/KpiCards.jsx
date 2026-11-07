// One strip of headline numbers instead of separate cards.
import { fmtMoney, fmtNumber } from "../format.js";

function Stat({ label, value, alert = false }) {
  return (
    <div className={alert ? "stat alert" : "stat"}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

export default function KpiCards({ analytics: a }) {
  const show = (fn) => (a ? fn(a) : "–");
  return (
    <section className="stats" aria-label="Summary">
      <Stat label="Products" value={show((x) => fmtNumber(x.total_products))} />
      <Stat label="Units on shelves" value={show((x) => fmtNumber(x.total_units))} />
      <Stat label="Stock value" value={show((x) => fmtMoney(x.inventory_value))} />
      <Stat label="Sold today" value={show((x) => fmtNumber(x.units_sold_today))} />
      <Stat label="Need restocking" value={show((x) => fmtNumber(x.by_status.LOW + x.by_status.OUT))} alert />
    </section>
  );
}

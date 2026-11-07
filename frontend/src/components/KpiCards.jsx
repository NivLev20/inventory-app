// The 4 summary cards at the top. A small reusable <Kpi> component is used 4 times.
import { fmtMoney, fmtNumber } from "../format.js";

function Kpi({ label, value, alert = false }) {
  return (
    <div className={alert ? "kpi alert" : "kpi"}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
    </div>
  );
}

export default function KpiCards({ analytics }) {
  // Before the first load, show dashes instead of numbers
  const a = analytics;
  return (
    <section className="kpis">
      <Kpi label="Products" value={a ? fmtNumber(a.total_products) : "–"} />
      <Kpi label="Units in stock" value={a ? fmtNumber(a.total_units) : "–"} />
      <Kpi label="Inventory value" value={a ? fmtMoney(a.inventory_value) : "–"} />
      <Kpi
        label="Need restock"
        value={a ? fmtNumber(a.by_status.LOW + a.by_status.OUT) : "–"}
        alert
      />
    </section>
  );
}

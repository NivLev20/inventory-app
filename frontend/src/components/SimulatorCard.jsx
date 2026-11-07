// Controls for the store simulator that runs as Kubernetes CronJobs.
import { useState } from "react";

export default function SimulatorCard({ enabled, onToggle, onRush }) {
  const [busy, setBusy] = useState(false);
  const known = enabled !== null;

  async function run(action) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel sim-card">
      <div className="sim-row">
        <h2>Store simulator</h2>
        {known && <span className={enabled ? "sim-state on" : "sim-state"}>{enabled ? "Running" : "Paused"}</span>}
      </div>
      <p className="muted">Customers buy every minute; a new product arrives every two minutes.</p>
      <div className="sim-actions">
        <button className="btn" disabled={!known || busy} onClick={() => run(() => onToggle(!enabled))}>
          {enabled ? "Pause" : "Resume"}
        </button>
        <button className="btn primary" disabled={busy} onClick={() => run(onRush)}>
          Start rush hour
        </button>
      </div>
    </section>
  );
}

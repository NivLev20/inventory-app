// Controls for the store simulator that runs as Kubernetes CronJobs.
import { useState } from "react";

export default function SimulatorCard({ enabled, onToggle, onRush }) {
  const [busy, setBusy] = useState(false);

  async function run(action) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  }

  const known = enabled !== null;

  return (
    <section className="card sim-card">
      <div className="sim-text">
        <h2>Store simulator</h2>
        <p className="muted">
          Customer purchases every minute, a new product every two minutes.{" "}
          {known && (
            <span className={enabled ? "pill OK" : "pill LOW"}>{enabled ? "Running" : "Paused"}</span>
          )}
        </p>
      </div>
      <div className="sim-actions">
        <button className="btn" disabled={!known || busy} onClick={() => run(() => onToggle(!enabled))}>
          {enabled ? "Pause" : "Resume"}
        </button>
        <button className="btn primary" disabled={busy} onClick={() => run(onRush)}>
          Rush hour
        </button>
      </div>
    </section>
  );
}

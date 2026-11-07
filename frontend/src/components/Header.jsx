// Top bar: chain name, API connection state and the main actions.
export default function Header({ apiUp, onAddClick }) {
  const status = apiUp === null ? "Connecting" : apiUp ? "Connected" : "Offline";
  const statusClass = "api-status" + (apiUp === true ? " up" : apiUp === false ? " down" : "");

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <h1>Smart Retail Inventory</h1>
          <p className="sub">Tel Aviv, Haifa and Jerusalem stores</p>
        </div>
        <div className="topbar-right">
          <span className={statusClass}>{status}</span>
          <a className="btn" href="/api/docs" target="_blank" rel="noreferrer">API docs</a>
          <button className="btn primary" onClick={onAddClick}>Add product</button>
        </div>
      </div>
    </header>
  );
}

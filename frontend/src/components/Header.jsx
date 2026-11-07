// Top bar: title, API status dot, and the "Add product" button.
// Props: apiUp (true/false/null), onAddClick (function)
export default function Header({ apiUp, onAddClick }) {
  let statusText = "Checking API…";
  let statusClass = "api-status";
  if (apiUp === true) {
    statusText = "API online";
    statusClass += " up";
  } else if (apiUp === false) {
    statusText = "API offline";
    statusClass += " down";
  }

  return (
    <header className="topbar">
      <div className="brand">
        <span className="logo" aria-hidden="true">▣</span>
        <div>
          <h1>Smart Retail Inventory</h1>
          <p className="sub">Stock levels across all stores</p>
        </div>
      </div>
      <div className="topbar-right">
        <span className={statusClass}>{statusText}</span>
        <button className="btn primary" onClick={onAddClick}>+ Add product</button>
      </div>
    </header>
  );
}

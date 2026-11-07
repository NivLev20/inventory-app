function BoxIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 8 12 3 3 8v8l9 5 9-5z" />
      <path d="m3 8 9 5 9-5M12 13v8" />
    </svg>
  );
}

function ThemeIcon({ theme }) {
  return theme === "dark" ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  );
}

export default function Header({ apiUp, theme, onToggleTheme, onAddClick }) {
  const status = apiUp === null ? "Connecting" : apiUp ? "Connected" : "Offline";
  const statusClass = "api-status" + (apiUp === true ? " up" : apiUp === false ? " down" : "");
  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <span className="brand-mark"><BoxIcon /></span>
          <div>
            <h1>Smart Retail Inventory</h1>
            <p className="sub">Tel Aviv, Haifa and Jerusalem stores</p>
          </div>
        </div>
        <div className="topbar-right">
          <span className={statusClass}>{status}</span>
          <button className="btn icon ghost" onClick={onToggleTheme}
                  aria-label={`Switch to ${nextTheme} mode`} title={`Switch to ${nextTheme} mode`}>
            <ThemeIcon theme={theme} />
          </button>
          <a className="btn ghost" href="/api/docs" target="_blank" rel="noreferrer">API docs</a>
          <button className="btn primary" onClick={onAddClick}>Add product</button>
        </div>
      </div>
    </header>
  );
}

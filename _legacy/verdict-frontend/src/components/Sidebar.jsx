export default function Sidebar({
  activeTab,
  setActiveTab,
  toggleTheme,
  isDark,
}) {
  return (
    <aside className="sidebar glass">
      <div className="sidebar-header">
        <img
          alt="Verdict Protocol logo"
          className="sidebar-logo"
          src="/assets/agent_court_logo_light.png"
        />
        <div className="hero-brand">
          <img
            alt="Verdict Protocol"
            src="/assets/agent_court_favicon_light.png"
          />
          <span>Ayush + Karan</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        <button
          className={`tab-btn ${activeTab === "tab-control" ? "active" : ""}`}
          onClick={() => setActiveTab("tab-control")}
        >
          Control Panel
        </button>
        <button
          className={`tab-btn ${activeTab === "tab-court" ? "active" : ""}`}
          onClick={() => setActiveTab("tab-court")}
        >
          Court Dashboard
        </button>
        <button
          className={`tab-btn ${activeTab === "tab-network" ? "active" : ""}`}
          onClick={() => setActiveTab("tab-network")}
        >
          Network Explorer
        </button>
        <button
          className="tab-btn"
          onClick={toggleTheme}
          style={{ marginTop: "auto", justifyContent: "center", gap: "8px" }}
        >
          {isDark ? "☀ Light Mode" : "☾ Dark Mode"}
        </button>
      </nav>
      <div className="footer">
        Source:
        <a
          className="inline-link"
          href="https://github.com/Ayush10/escrow"
          target="_blank"
          rel="noreferrer"
        >
          github.com/Ayush10/escrow
        </a>
      </div>
    </aside>
  );
}

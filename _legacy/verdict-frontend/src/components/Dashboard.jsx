import { useState, useEffect } from "react";
import Sidebar from "./Sidebar";
import ControlPanel from "./ControlPanel";
import CourtDashboard from "./CourtDashboard";
import NetworkExplorer from "./NetworkExplorer";

export default function Dashboard(props) {
  const [activeTab, setActiveTab] = useState("tab-control");
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Initial theme load
    const savedTheme = localStorage.getItem("vp_theme");
    if (savedTheme === "dark") {
      setIsDark(true);
      document.body.classList.add("dark");
    } else {
      document.body.classList.remove("dark");
    }
  }, []);

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.body.classList.add("dark");
    } else {
      document.body.classList.remove("dark");
    }
    localStorage.setItem("vp_theme", nextDark ? "dark" : "light");
  };

  return (
    <div className="dashboard-shell" id="appDashboard">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        toggleTheme={toggleTheme}
        isDark={isDark}
      />
      <main className="content">
        {activeTab === "tab-control" && <ControlPanel {...props} />}
        {activeTab === "tab-court" && <CourtDashboard {...props} />}
        {activeTab === "tab-network" && <NetworkExplorer {...props} />}
      </main>
    </div>
  );
}

import { useState } from "react";
import LandingPage from "./components/LandingPage";
import Dashboard from "./components/Dashboard";
import { useVerdictServices } from "./useVerdictServices";

function App() {
  const [showDemo, setShowDemo] = useState(false);
  const verdictServices = useVerdictServices();

  return (
    <>
      {!showDemo ? (
        <LandingPage
          onShowDemo={() => {
            setShowDemo(true);
            // auto connect when demo launches
            if (!verdictServices.isConnected) {
              verdictServices.connectAndRefresh();
            }
          }}
        />
      ) : (
        <Dashboard />
      )}
    </>
  );
}

export default App;

import { Routes, Route, Navigate } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { PipelinePage } from "./pages/PipelinePage";
import { AssetLibrary } from "./pages/AssetLibrary";
import { AssetDetail } from "./components/assets/AssetDetail";
import "./App.css";
import "./pages/AssetLibrary.css";

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/pipeline" element={<PipelinePage />} />
      <Route path="/assets" element={<AssetLibrary />} />
      <Route path="/assets/:assetId" element={<AssetDetail />} />
      <Route
        path="/generate/image"
        element={<Navigate to="/pipeline?tab=image" replace />}
      />
    </Routes>
  );
}

export default App;

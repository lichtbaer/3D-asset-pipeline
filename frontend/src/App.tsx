import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";
import { PipelinePage } from "./pages/PipelinePage";
import { AssetLibrary } from "./pages/AssetLibrary";
import { StoragePage } from "./pages/StoragePage";
import { PipelineStoreProvider } from "./store/PipelineStore";
import { ToastProvider } from "./components/ui/ToastContext.js";
import "./App.css";
import "./components/ui/ui.css";
import "./styles/buttons.css";
import "./pages/AssetLibrary.css";
import "./pages/StoragePage.css";

function App() {
  return (
    <PipelineStoreProvider>
      <ToastProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="pipeline" element={<PipelinePage />} />
            <Route path="assets" element={<AssetLibrary />} />
            <Route path="storage" element={<StoragePage />} />
          </Route>
          <Route
            path="/generate/image"
            element={<Navigate to="/pipeline?tab=image" replace />}
          />
        </Routes>
      </ToastProvider>
    </PipelineStoreProvider>
  );
}

export default App;

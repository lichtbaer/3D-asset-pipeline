import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";
import { PipelinePage } from "./pages/PipelinePage";
import { AssetLibrary } from "./pages/AssetLibrary";
import { PipelineStoreProvider } from "./store/PipelineStore";
import "./App.css";
import "./styles/buttons.css";
import "./pages/AssetLibrary.css";

function App() {
  return (
    <PipelineStoreProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="pipeline" element={<PipelinePage />} />
          <Route path="assets" element={<AssetLibrary />} />
        </Route>
        <Route
          path="/generate/image"
          element={<Navigate to="/pipeline?tab=image" replace />}
        />
      </Routes>
    </PipelineStoreProvider>
  );
}

export default App;

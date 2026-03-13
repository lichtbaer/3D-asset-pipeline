import { Routes, Route, Navigate } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { PipelinePage } from "./pages/PipelinePage";
import "./App.css";

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/pipeline" element={<PipelinePage />} />
      <Route
        path="/generate/image"
        element={<Navigate to="/pipeline?tab=image" replace />}
      />
    </Routes>
  );
}

export default App;

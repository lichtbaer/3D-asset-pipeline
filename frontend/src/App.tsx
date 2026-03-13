import { Routes, Route } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { ImageGenerationPage } from "./pages/ImageGenerationPage";
import "./App.css";

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/generate/image" element={<ImageGenerationPage />} />
    </Routes>
  );
}

export default App;

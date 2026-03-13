import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <main style={{ padding: "2rem", textAlign: "center" }}>
      <h1>Purzel ML Asset Pipeline</h1>
      <p>Placeholder-Startseite — bereit für PURZEL-002</p>
      <p>
        <Link to="/generate/image">Zur Bildgenerierung</Link>
      </p>
    </main>
  );
}

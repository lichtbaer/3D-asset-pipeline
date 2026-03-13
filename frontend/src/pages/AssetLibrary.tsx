import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listAssets, getAssetFileUrl } from "../api/assets.js";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("de-DE", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function StepBadges({ steps }: { steps: Record<string, { file: string }> }) {
  const hasImage = "image" in steps;
  const hasBgremoval = "bgremoval" in steps;
  const hasMesh = "mesh" in steps;
  return (
    <span className="asset-card__badges">
      {hasImage && <span title="Bild">🖼</span>}
      {hasBgremoval && <span title="Freistellung">✂️</span>}
      {hasMesh && <span title="Mesh">🧊</span>}
    </span>
  );
}

export function AssetLibrary() {
  const { data: assets, isLoading, error } = useQuery({
    queryKey: ["assets"],
    queryFn: listAssets,
  });

  const baseUrl =
    import.meta.env.VITE_API_URL || "http://localhost:8000";

  return (
    <main className="asset-library">
      <header className="asset-library__header">
        <h1>Asset-Bibliothek</h1>
        <p className="asset-library__subtitle">
          Alle gespeicherten Pipeline-Outputs (Bilder, Freistellungen, Meshes)
        </p>
        <Link to="/pipeline" className="asset-library__link">
          Zur Pipeline
        </Link>
      </header>

      {isLoading && !assets && (
        <div className="asset-library__loading">
          <div className="spinner" aria-hidden />
          <p>Assets werden geladen...</p>
        </div>
      )}

      {error && (
        <div className="asset-library__error">
          <p>
            Fehler beim Laden:{" "}
            {error instanceof Error ? error.message : "Unbekannter Fehler"}
          </p>
        </div>
      )}

      {assets && assets.length === 0 && (
        <div className="asset-library__empty">
          <p>Noch keine Assets gespeichert.</p>
          <p>
            Generiere ein Bild, führe eine Freistellung durch oder erstelle ein
            Mesh — abgeschlossene Jobs werden automatisch in der Bibliothek
            gespeichert.
          </p>
        </div>
      )}

      {assets && assets.length > 0 && (
        <div className="asset-library__grid">
          {assets.map((asset) => {
            const thumbUrl = asset.thumbnail_url
              ? `${baseUrl}${asset.thumbnail_url}`
              : null;
            return (
              <Link
                key={asset.asset_id}
                to={`/assets/${asset.asset_id}`}
                className="asset-card"
              >
                <div className="asset-card__thumb">
                  {thumbUrl ? (
                    <img
                      src={thumbUrl}
                      alt=""
                      className="asset-card__img"
                    />
                  ) : (
                    <div className="asset-card__placeholder">
                      <span>🧊</span>
                    </div>
                  )}
                </div>
                <div className="asset-card__meta">
                  <p className="asset-card__date">
                    {formatDate(asset.created_at)}
                  </p>
                  <StepBadges steps={asset.steps} />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </main>
  );
}

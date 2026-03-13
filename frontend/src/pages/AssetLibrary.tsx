import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listAssets } from "../api/assets.js";
import { AssetDetailModal } from "../components/assets/AssetDetailModal.js";

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

function StepBadges({ steps }: { steps: Record<string, { file?: string }> }) {
  const hasImage = "image" in steps;
  const hasBgremoval = "bgremoval" in steps;
  const hasMesh = "mesh" in steps;
  const hasRigging = "rigging" in steps;
  const hasAnimation = "animation" in steps;
  return (
    <span className="asset-card__badges">
      <span
        title="Bild"
        className={hasImage ? "" : "asset-card__badge--missing"}
      >
        🖼
      </span>
      <span
        title="Freistellung"
        className={hasBgremoval ? "" : "asset-card__badge--missing"}
      >
        ✂️
      </span>
      <span
        title="Mesh"
        className={hasMesh ? "" : "asset-card__badge--missing"}
      >
        🧊
      </span>
      <span
        title="Rigging"
        className={hasRigging ? "" : "asset-card__badge--missing"}
      >
        🦴
      </span>
      <span
        title="Animation"
        className={hasAnimation ? "" : "asset-card__badge--missing"}
      >
        🎬
      </span>
    </span>
  );
}

export function AssetLibrary() {
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

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
          <p>Noch keine Assets generiert.</p>
          <Link to="/pipeline" className="asset-library__empty-link">
            Zur Pipeline →
          </Link>
        </div>
      )}

      {assets && assets.length > 0 && (
        <div className="asset-library__grid">
          {assets.map((asset) => {
            const thumbUrl = asset.thumbnail_url
              ? `${baseUrl}${asset.thumbnail_url}`
              : null;
            return (
              <button
                key={asset.asset_id}
                type="button"
                className="asset-card"
                onClick={() => setSelectedAssetId(asset.asset_id)}
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
              </button>
            );
          })}
        </div>
      )}

      {selectedAssetId && (
        <AssetDetailModal
          assetId={selectedAssetId}
          onClose={() => setSelectedAssetId(null)}
        />
      )}
    </main>
  );
}

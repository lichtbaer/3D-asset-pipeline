import { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listAssets } from "../api/assets.js";
import { getSketchfabStatus } from "../api/sketchfab.js";
import { AssetDetailModal } from "../components/assets/AssetDetailModal.js";
import { AssetUploadZone } from "../components/assets/AssetUploadZone.js";
import { SketchfabImportModal } from "../components/assets/SketchfabImportModal.js";
import type { AssetListItem } from "../api/assets.js";

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

function AssetCardActions({
  asset,
  onNavigate,
  onClick,
}: {
  asset: AssetListItem;
  onNavigate: (tab: string, assetId: string) => void;
  onClick: (e: React.MouseEvent) => void;
}) {
  const hasMesh = "mesh" in asset.steps && asset.steps.mesh?.file;
  const hasRigging = "rigging" in asset.steps && asset.steps.rigging?.file;

  if (!hasMesh && !hasRigging) return null;

  return (
    <div className="asset-card__actions" onClick={onClick}>
      {hasMesh && (
        <>
          <button
            type="button"
            className="btn btn--outline btn--sm"
            onClick={(e) => {
              e.stopPropagation();
              onNavigate("rigging", asset.asset_id);
            }}
          >
            → Riggen
          </button>
          <button
            type="button"
            className="btn btn--outline btn--sm"
            onClick={(e) => {
              e.stopPropagation();
              onNavigate("mesh-processing", asset.asset_id);
            }}
          >
            → Mesh-Processing
          </button>
        </>
      )}
      {hasRigging && (
        <>
          <button
            type="button"
            className="btn btn--outline btn--sm"
            onClick={(e) => {
              e.stopPropagation();
              onNavigate("animation", asset.asset_id);
            }}
          >
            → Animieren
          </button>
          <button
            type="button"
            className="btn btn--outline btn--sm"
            onClick={(e) => {
              e.stopPropagation();
              onNavigate("rigging", asset.asset_id);
            }}
          >
            → Riggen (erneut)
          </button>
        </>
      )}
    </div>
  );
}

export function AssetLibrary() {
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [showSketchfabImport, setShowSketchfabImport] = useState(false);

  const { data: sketchfabEnabled } = useQuery({
    queryKey: ["sketchfab-status"],
    queryFn: getSketchfabStatus,
  });

  useEffect(() => {
    const state = location.state as { importedAssetId?: string } | null;
    if (state?.importedAssetId) {
      setSelectedAssetId(state.importedAssetId);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, location.pathname, navigate]);

  const { data: assets, isLoading, error } = useQuery({
    queryKey: ["assets"],
    queryFn: listAssets,
  });

  const baseUrl =
    import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleNavigateToPipeline = (tab: string, assetId: string) => {
    navigate(`/pipeline?tab=${tab}&assetId=${encodeURIComponent(assetId)}`);
  };

  return (
    <main className="asset-library">
      <header className="asset-library__header">
        <h1>Asset-Bibliothek</h1>
        <p className="asset-library__subtitle">
          Alle gespeicherten Pipeline-Outputs (Bilder, Freistellungen, Meshes)
        </p>
        <div className="asset-library__header-actions">
          {sketchfabEnabled?.enabled && (
            <button
              type="button"
              className="btn btn--outline"
              onClick={() => setShowSketchfabImport(true)}
            >
              Von Sketchfab importieren
            </button>
          )}
          <Link to="/pipeline" className="asset-library__link">
            Zur Pipeline
          </Link>
        </div>
      </header>

      <div className="asset-library__upload-row">
        <AssetUploadZone type="image" />
        <AssetUploadZone type="mesh" />
      </div>

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
              <div key={asset.asset_id} className="asset-card-wrapper">
                <button
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
                <AssetCardActions
                  asset={asset}
                  onNavigate={handleNavigateToPipeline}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
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
      {showSketchfabImport && (
        <SketchfabImportModal onClose={() => setShowSketchfabImport(false)} />
      )}
    </main>
  );
}

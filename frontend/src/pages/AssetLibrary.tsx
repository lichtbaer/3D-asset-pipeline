import { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listAssets,
  deleteAsset,
  deleteAssetBatch,
  restoreAsset,
} from "../api/assets.js";
import { getSketchfabStatus } from "../api/sketchfab.js";
import { AssetDetailModal } from "../components/assets/AssetDetailModal.js";
import { AssetUploadZone } from "../components/assets/AssetUploadZone.js";
import { SketchfabImportModal } from "../components/assets/SketchfabImportModal.js";
import { DeleteAssetDialog } from "../components/assets/DeleteAssetDialog.js";
import { TrashActionsDialog } from "../components/assets/TrashActionsDialog.js";
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
  isTrashView,
  onNavigate,
  onClick,
}: {
  asset: AssetListItem;
  isTrashView: boolean;
  onNavigate: (tab: string, assetId: string) => void;
  onDelete: (e: React.MouseEvent, assetId: string) => void;
  onTrashAction: (e: React.MouseEvent, assetId: string) => void;
  onClick: (e: React.MouseEvent) => void;
}) {
  const hasMesh = "mesh" in asset.steps && asset.steps.mesh?.file;
  const hasRigging = "rigging" in asset.steps && asset.steps.rigging?.file;

  if (isTrashView) return null;

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
  const queryClient = useQueryClient();
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [showSketchfabImport, setShowSketchfabImport] = useState(false);
  const [showTrash, setShowTrash] = useState(false);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleteDialog, setDeleteDialog] = useState<{
    mode: "single" | "batch" | "purge";
    asset?: AssetListItem | null;
    assetCount?: number;
    purgeCount?: number;
    purgeSize?: string;
  } | null>(null);
  const [trashActionAsset, setTrashActionAsset] = useState<AssetListItem | null>(
    null
  );

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
    queryKey: ["assets", showTrash],
    queryFn: () => listAssets({ includeDeleted: showTrash }),
  });

  const baseUrl =
    import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleNavigateToPipeline = (tab: string, assetId: string) => {
    navigate(`/pipeline?tab=${tab}&assetId=${encodeURIComponent(assetId)}`);
  };

  const handleDeleteClick = (e: React.MouseEvent, assetId: string) => {
    e.stopPropagation();
    const asset = assets?.find((a) => a.asset_id === assetId);
    if (asset) setDeleteDialog({ mode: "single", asset });
  };

  const handleTrashActionClick = (e: React.MouseEvent, assetId: string) => {
    e.stopPropagation();
    const asset = assets?.find((a) => a.asset_id === assetId);
    if (asset) setTrashActionAsset(asset);
  };

  const handleConfirmDelete = async () => {
    if (!deleteDialog) return;
    if (deleteDialog.mode === "single" && deleteDialog.asset) {
      await deleteAsset(deleteDialog.asset.asset_id, false);
    } else if (deleteDialog.mode === "batch" && deleteDialog.assetCount) {
      await deleteAssetBatch(Array.from(selectedIds), false);
      setSelectedIds(new Set());
      setSelectMode(false);
    }
    setDeleteDialog(null);
    void queryClient.invalidateQueries({ queryKey: ["assets"] });
    void queryClient.invalidateQueries({ queryKey: ["storage"] });
  };

  const handleConfirmRestore = async () => {
    if (trashActionAsset) {
      await restoreAsset(trashActionAsset.asset_id);
      setTrashActionAsset(null);
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
    }
  };

  const handleConfirmPermanentDelete = async () => {
    if (trashActionAsset) {
      await deleteAsset(trashActionAsset.asset_id, true);
      setTrashActionAsset(null);
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      void queryClient.invalidateQueries({ queryKey: ["storage"] });
    }
  };

  const toggleSelect = (assetId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(assetId)) next.delete(assetId);
      else next.add(assetId);
      return next;
    });
  };

  const displayAssets = showTrash
    ? assets?.filter((a) => a.deleted_at) ?? []
    : assets?.filter((a) => !a.deleted_at) ?? [];

  return (
    <main className="asset-library">
      <header className="asset-library__header">
        <h1>Asset-Bibliothek</h1>
        <p className="asset-library__subtitle">
          Alle gespeicherten Pipeline-Outputs (Bilder, Freistellungen, Meshes)
        </p>
        <div className="asset-library__header-actions">
          <label className="asset-library__trash-toggle">
            <input
              type="checkbox"
              checked={showTrash}
              onChange={(e) => setShowTrash(e.target.checked)}
            />
            Papierkorb anzeigen
          </label>
          {!showTrash && (
            <button
              type="button"
              className="btn btn--outline"
              onClick={() => {
                setSelectMode(!selectMode);
                if (selectMode) setSelectedIds(new Set());
              }}
            >
              {selectMode ? "Abbrechen" : "Auswählen"}
            </button>
          )}
          {sketchfabEnabled?.enabled && (
            <button
              type="button"
              className="btn btn--outline"
              onClick={() => setShowSketchfabImport(true)}
            >
              Von Sketchfab importieren
            </button>
          )}
          <Link to="/storage" className="asset-library__link">
            Speicher
          </Link>
          <Link to="/pipeline" className="asset-library__link">
            Zur Pipeline
          </Link>
        </div>
      </header>

      {selectMode && selectedIds.size > 0 && (
        <div className="asset-library__select-bar">
          <span>{selectedIds.size} ausgewählt</span>
          <button
            type="button"
            className="btn btn--outline"
            onClick={() =>
              setDeleteDialog({
                mode: "batch",
                assetCount: selectedIds.size,
              })
            }
          >
            {selectedIds.size} Assets löschen
          </button>
        </div>
      )}

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

      {assets && displayAssets.length === 0 && (
        <div className="asset-library__empty">
          <p>
            {showTrash
              ? "Papierkorb ist leer."
              : "Noch keine Assets generiert."}
          </p>
          {!showTrash && (
            <Link to="/pipeline" className="asset-library__empty-link">
              Zur Pipeline →
            </Link>
          )}
        </div>
      )}

      {displayAssets.length > 0 && (
        <div className="asset-library__grid">
          {displayAssets.map((asset) => {
            const thumbUrl = asset.thumbnail_url
              ? `${baseUrl}${asset.thumbnail_url}`
              : null;
            const isDeleted = !!asset.deleted_at;
            const isSelected = selectedIds.has(asset.asset_id);
            return (
              <div
                key={asset.asset_id}
                className={`asset-card-wrapper ${isSelected ? "asset-card-wrapper--selected" : ""} ${isDeleted ? "asset-card-wrapper--deleted" : ""}`}
              >
                {selectMode && !showTrash && (
                  <input
                    type="checkbox"
                    className="asset-card__checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(asset.asset_id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                )}
                {!selectMode && !isDeleted && (
                  <button
                    type="button"
                    className="asset-card__delete-btn"
                    onClick={(e) => handleDeleteClick(e, asset.asset_id)}
                    title="In Papierkorb"
                    aria-label="In Papierkorb verschieben"
                  >
                    🗑
                  </button>
                )}
                <button
                  type="button"
                  className={`asset-card ${isDeleted ? "asset-card--deleted" : ""}`}
                  onClick={() => {
                    if (isDeleted) {
                      setTrashActionAsset(asset);
                    } else {
                      setSelectedAssetId(asset.asset_id);
                    }
                  }}
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
                  isTrashView={isDeleted}
                  onNavigate={handleNavigateToPipeline}
                  onDelete={handleDeleteClick}
                  onTrashAction={handleTrashActionClick}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            );
          })}
        </div>
      )}

      {selectedAssetId && !assets?.some((a) => a.asset_id === selectedAssetId && a.deleted_at) && (
        <AssetDetailModal
          assetId={selectedAssetId}
          onClose={() => setSelectedAssetId(null)}
        />
      )}
      {showSketchfabImport && (
        <SketchfabImportModal onClose={() => setShowSketchfabImport(false)} />
      )}

      {deleteDialog && (
        <DeleteAssetDialog
          asset={deleteDialog.asset ?? null}
          assetCount={deleteDialog.assetCount}
          mode={deleteDialog.mode}
          purgeCount={deleteDialog.purgeCount}
          purgeSize={deleteDialog.purgeSize}
          onConfirm={handleConfirmDelete}
          onCancel={() => setDeleteDialog(null)}
        />
      )}

      {trashActionAsset && (
        <div className="delete-dialog-overlay" onClick={() => setTrashActionAsset(null)}>
          <div onClick={(e) => e.stopPropagation()}>
            <TrashActionsDialog
              asset={trashActionAsset}
              onRestore={handleConfirmRestore}
              onPermanentDelete={handleConfirmPermanentDelete}
              onCancel={() => setTrashActionAsset(null)}
            />
          </div>
        </div>
      )}
    </main>
  );
}

import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listAssets,
  deleteAsset,
  deleteAssetBatch,
  restoreAsset,
  patchAssetMeta,
} from "../api/assets.js";
import { getSketchfabStatus } from "../api/sketchfab.js";
import { AssetDetailModal } from "../components/assets/AssetDetailModal.js";
import { AssetUploadZone } from "../components/assets/AssetUploadZone.js";
import { SketchfabImportModal } from "../components/assets/SketchfabImportModal.js";
import { DeleteAssetDialog } from "../components/assets/DeleteAssetDialog.js";
import { TrashActionsDialog } from "../components/assets/TrashActionsDialog.js";
import { AssetPickerModal } from "../components/assets/AssetPickerModal.js";
import { ApplyPresetModal } from "../components/presets/ApplyPresetModal.js";
import { getUrlForFirstApplicableStep } from "../utils/presetNavigation.js";
import { useDebounce } from "../hooks/useDebounce.js";
import { usePipelineStore } from "../store/PipelineStore.js";
import type {
  AssetListItem,
  ListAssetsParams,
} from "../api/assets.js";

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

function RatingStars({
  rating,
  onRate,
  onClick,
}: {
  rating: number | null | undefined;
  onRate: (r: number) => void;
  onClick: (e: React.MouseEvent) => void;
}) {
  const r = rating ?? 0;
  return (
    <span
      className="asset-card__rating"
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
        }
      }}
      role="group"
      aria-label={`Bewertung: ${r} von 5 Sternen`}
    >
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i}
          type="button"
          className="asset-card__star"
          aria-label={`${i} Sterne`}
          onClick={(e) => {
            e.stopPropagation();
            onRate(i);
          }}
        >
          {i <= r ? "★" : "☆"}
        </button>
      ))}
    </span>
  );
}

function FavoritButton({
  favorited,
  onToggle,
}: {
  favorited: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className={`asset-card__favorit ${favorited ? "asset-card__favorit--on" : ""}`}
      aria-label={favorited ? "Aus Favoriten entfernen" : "Als Favorit markieren"}
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
    >
      {favorited ? "♥" : "♡"}
    </button>
  );
}

function TagsChips({
  tags,
  maxVisible = 3,
}: {
  tags: string[];
  maxVisible?: number;
}) {
  const visible = tags.slice(0, maxVisible);
  const rest = tags.length - maxVisible;
  if (tags.length === 0) return null;
  return (
    <span className="asset-card__tags">
      {visible.map((t) => (
        <span key={t} className="asset-card__tag">
          {t}
        </span>
      ))}
      {rest > 0 && (
        <span className="asset-card__tag asset-card__tag--more">
          +{rest}
        </span>
      )}
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

const SORT_OPTIONS: { value: ListAssetsParams["sort"]; label: string }[] = [
  { value: "created_desc", label: "Neueste" },
  { value: "created_asc", label: "Älteste" },
  { value: "name", label: "Name" },
  { value: "rating", label: "Rating" },
];

const STEP_OPTIONS: { value: ListAssetsParams["has_step"]; label: string }[] = [
  { value: undefined, label: "Alle" },
  { value: "image", label: "Bild" },
  { value: "mesh", label: "Mesh" },
  { value: "rigging", label: "Rig" },
  { value: "animation", label: "Animation" },
];

export function AssetLibrary() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { setActiveAssetId } = usePipelineStore();
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [lastUploadedAssetId, setLastUploadedAssetId] = useState<
    string | null
  >(null);
  const [showSketchfabImport, setShowSketchfabImport] = useState(false);
  const [showApplyPreset, setShowApplyPreset] = useState(false);
  const [applyPresetAssetId, setApplyPresetAssetId] = useState<string | null>(
    null
  );
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
  const [searchInput, setSearchInput] = useState("");
  const [filterFavorited, setFilterFavorited] = useState<boolean | undefined>(
    undefined
  );
  const [filterTags, setFilterTags] = useState<string[]>([]);
  const [filterTagInput, setFilterTagInput] = useState("");
  const [filterStep, setFilterStep] = useState<
    ListAssetsParams["has_step"]
  >(undefined);
  const [filterSort, setFilterSort] = useState<ListAssetsParams["sort"]>(
    "created_desc"
  );
  const [showFilterDropdown, setShowFilterDropdown] = useState(false);

  const debouncedSearch = useDebounce(searchInput, 300);

  const { data: sketchfabEnabled } = useQuery({
    queryKey: ["sketchfab-status"],
    queryFn: getSketchfabStatus,
  });

  const assetIdFromUrl = new URLSearchParams(location.search).get("assetId");

  useEffect(() => {
    const state = location.state as { importedAssetId?: string } | null;
    if (state?.importedAssetId) {
      setSelectedAssetId(state.importedAssetId);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, location.pathname, navigate]);

  useEffect(() => {
    if (assetIdFromUrl) {
      setSelectedAssetId(assetIdFromUrl);
    }
  }, [assetIdFromUrl]);

  const listParams = useMemo(
    () => ({
      search: debouncedSearch.trim() || undefined,
      tags: filterTags.length > 0 ? filterTags.join(",") : undefined,
      has_step: filterStep,
      favorited: filterFavorited,
      sort: filterSort,
      includeDeleted: showTrash,
    }),
    [
      debouncedSearch,
      filterTags,
      filterStep,
      filterFavorited,
      filterSort,
      showTrash,
    ]
  );

  const { data: assets, isLoading, error } = useQuery({
    queryKey: ["assets", listParams],
    queryFn: () => listAssets(listParams),
  });

  const hasActiveFilters =
    debouncedSearch.trim() !== "" ||
    filterFavorited !== undefined ||
    filterTags.length > 0 ||
    filterStep !== undefined ||
    filterSort !== "created_desc";

  const clearAllFilters = () => {
    setSearchInput("");
    setFilterFavorited(undefined);
    setFilterTags([]);
    setFilterStep(undefined);
    setFilterSort("created_desc");
  };

  const removeFilterTag = (tag: string) => {
    setFilterTags((prev) => prev.filter((t) => t !== tag));
  };

  const addFilterTag = (tag: string) => {
    const t = tag.trim().toLowerCase();
    if (t && !filterTags.includes(t)) {
      setFilterTags((prev) => [...prev, t]);
      setFilterTagInput("");
    }
  };

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

  const handleRateAsset = async (assetId: string, rating: number) => {
    try {
      await patchAssetMeta(assetId, { rating });
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      void queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
    } catch {
      // Fehler ignorieren
    }
  };

  const handleToggleFavorit = async (assetId: string, favorited: boolean) => {
    try {
      await patchAssetMeta(assetId, { favorited });
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      void queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
    } catch {
      // Fehler ignorieren
    }
  };

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
          <button
            type="button"
            className="btn btn--outline"
            onClick={() => setShowApplyPreset(true)}
          >
            ⚡ Preset anwenden
          </button>
          <Link to="/presets" className="asset-library__link">
            Presets
          </Link>
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
        <AssetUploadZone
          type="image"
          onSuccess={(assetId) => {
            setSelectedAssetId(assetId);
            setLastUploadedAssetId(assetId);
          }}
        />
        <AssetUploadZone
          type="mesh"
          onSuccess={(assetId) => {
            setSelectedAssetId(assetId);
            setLastUploadedAssetId(assetId);
          }}
        />
      </div>

      <div className="asset-library__search-row">
        <div className="asset-library__search-wrap">
          <span className="asset-library__search-icon" aria-hidden>
            🔍
          </span>
          <input
            type="search"
            className="asset-library__search-input"
            placeholder="Assets suchen (Name, Prompt, Tags)..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            aria-label="Assets suchen"
          />
        </div>
        <button
          type="button"
          className={`btn btn--outline asset-library__favoriten-btn ${
            filterFavorited ? "btn--active" : ""
          }`}
          onClick={() => setFilterFavorited((v) => (v ? undefined : true))}
          aria-pressed={filterFavorited ?? false}
        >
          ☆ Favoriten
        </button>
        <div className="asset-library__filter-dropdown">
          <button
            type="button"
            className="btn btn--outline"
            onClick={() => setShowFilterDropdown((v) => !v)}
            aria-expanded={showFilterDropdown}
            aria-haspopup="true"
          >
            Filter ▾
          </button>
          {showFilterDropdown && (
            <div className="asset-library__filter-panel">
              <div className="asset-library__filter-group">
                <label className="asset-library__filter-label">Step:</label>
                <select
                  value={filterStep ?? ""}
                  onChange={(e) =>
                    setFilterStep(
                      (e.target.value || undefined) as ListAssetsParams["has_step"]
                    )
                  }
                >
                  {STEP_OPTIONS.map((o) => (
                    <option key={o.value ?? "all"} value={o.value ?? ""}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="asset-library__filter-group">
                <label className="asset-library__filter-label">Sort:</label>
                <select
                  value={filterSort}
                  onChange={(e) =>
                    setFilterSort(e.target.value as ListAssetsParams["sort"])
                  }
                >
                  {SORT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      {hasActiveFilters && (
        <div className="asset-library__filter-chips">
          {filterTags.map((t) => (
            <span key={t} className="asset-library__chip">
              {t}{" "}
              <button
                type="button"
                onClick={() => removeFilterTag(t)}
                aria-label={`Tag ${t} entfernen`}
              >
                ×
              </button>
            </span>
          ))}
          <div className="asset-library__chip-input-wrap">
            <input
              type="text"
              className="asset-library__chip-input"
              placeholder="+ Tag hinzufügen"
              value={filterTagInput}
              onChange={(e) => setFilterTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  addFilterTag(filterTagInput);
                }
              }}
            />
          </div>
          <button
            type="button"
            className="asset-library__clear-filters"
            onClick={clearAllFilters}
          >
            Alle Filter löschen
          </button>
        </div>
      )}

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
            const tags = asset.tags ?? [];
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
                    <FavoritButton
                      favorited={asset.favorited ?? false}
                      onToggle={() =>
                        handleToggleFavorit(
                          asset.asset_id,
                          !(asset.favorited ?? false)
                        )
                      }
                    />
                  </div>
                  <div className="asset-card__meta">
                    <p className="asset-card__date">
                      {asset.name ?? formatDate(asset.created_at)}
                    </p>
                    <RatingStars
                      rating={asset.rating ?? null}
                      onRate={(r) => handleRateAsset(asset.asset_id, r)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <TagsChips tags={tags} maxVisible={3} />
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
          onClose={() => {
            setSelectedAssetId(null);
            setLastUploadedAssetId(null);
          }}
          initialShowTagSuggestions={selectedAssetId === lastUploadedAssetId}
          onAssetUpdate={() => {
            void queryClient.invalidateQueries({ queryKey: ["assets"] });
          }}
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

      {showApplyPreset && (
        <>
          {!applyPresetAssetId ? (
            <AssetPickerModal
              isOpen={true}
              onClose={() => {
                setShowApplyPreset(false);
                setApplyPresetAssetId(null);
              }}
              onSelect={(asset) => {
                setApplyPresetAssetId(asset.asset_id);
              }}
              filter="has_mesh"
            />
          ) : (
            <ApplyPresetModal
              assetId={applyPresetAssetId}
              onClose={() => {
                setShowApplyPreset(false);
                setApplyPresetAssetId(null);
              }}
              onExecutePlan={(plan) => {
                setActiveAssetId(plan.asset_id);
                setApplyPresetAssetId(null);
                setShowApplyPreset(false);
                const url = getUrlForFirstApplicableStep(
                  plan.execution_plan,
                  plan.asset_id
                );
                navigate(url);
              }}
            />
          )}
        </>
      )}
    </main>
  );
}

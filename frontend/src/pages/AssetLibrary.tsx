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
import { API_BASE } from "../api/client.js";
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
import { AssetFilterBar } from "../components/assets/AssetFilterBar.js";
import { AssetGrid } from "../components/assets/AssetGrid.js";
import type {
  AssetListItem,
  ListAssetsParams,
} from "../api/assets.js";

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

  const baseUrl = API_BASE;

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

      <AssetFilterBar
        searchInput={searchInput}
        setSearchInput={setSearchInput}
        filterFavorited={filterFavorited}
        setFilterFavorited={setFilterFavorited}
        filterStep={filterStep}
        setFilterStep={setFilterStep}
        filterSort={filterSort}
        setFilterSort={setFilterSort}
        showFilterDropdown={showFilterDropdown}
        setShowFilterDropdown={setShowFilterDropdown}
        filterTags={filterTags}
        filterTagInput={filterTagInput}
        setFilterTagInput={setFilterTagInput}
        addFilterTag={addFilterTag}
        removeFilterTag={removeFilterTag}
        hasActiveFilters={hasActiveFilters}
        clearAllFilters={clearAllFilters}
      />

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

      <AssetGrid
        displayAssets={displayAssets}
        baseUrl={baseUrl}
        selectMode={selectMode}
        showTrash={showTrash}
        selectedIds={selectedIds}
        toggleSelect={toggleSelect}
        handleDeleteClick={handleDeleteClick}
        handleTrashActionClick={handleTrashActionClick}
        handleNavigateToPipeline={handleNavigateToPipeline}
        handleRateAsset={handleRateAsset}
        handleToggleFavorit={handleToggleFavorit}
        setSelectedAssetId={setSelectedAssetId}
        setTrashActionAsset={setTrashActionAsset}
      />

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

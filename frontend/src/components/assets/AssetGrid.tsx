import { useState } from "react";
import { ImageIcon, ScissorsIcon, CubeIcon, BoneIcon, FilmIcon } from "../icons/index.js";
import type { AssetListItem } from "../../api/assets.js";
import { renderAssetPreview } from "../../api/assets.js";

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

function QualityBadge({ qualityGate }: { qualityGate: import("../../api/assets.js").QualityGate | null | undefined }) {
  if (!qualityGate) return null;
  const color =
    qualityGate.rigging_suitable
      ? qualityGate.score >= 7
        ? "var(--color-success, #2e7d32)"
        : "var(--color-warning, #f59e0b)"
      : "var(--color-error, #c62828)";
  const label = qualityGate.rigging_suitable ? `Q${qualityGate.score}` : `Q${qualityGate.score}!`;
  const title = qualityGate.rigging_suitable
    ? `Qualitätsbewertung: ${qualityGate.score}/10`
    : `Qualitätsbewertung: ${qualityGate.score}/10 — Rigging nicht empfohlen`;
  return (
    <span
      className="asset-card__quality-badge"
      style={{ color, borderColor: color }}
      title={title}
      aria-label={title}
    >
      {label}
    </span>
  );
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
        <ImageIcon size={14} />
      </span>
      <span
        title="Freistellung"
        className={hasBgremoval ? "" : "asset-card__badge--missing"}
      >
        <ScissorsIcon size={14} />
      </span>
      <span
        title="Mesh"
        className={hasMesh ? "" : "asset-card__badge--missing"}
      >
        <CubeIcon size={14} />
      </span>
      <span
        title="Rigging"
        className={hasRigging ? "" : "asset-card__badge--missing"}
      >
        <BoneIcon size={14} />
      </span>
      <span
        title="Animation"
        className={hasAnimation ? "" : "asset-card__badge--missing"}
      >
        <FilmIcon size={14} />
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
  onPreviewRendered,
}: {
  asset: AssetListItem;
  isTrashView: boolean;
  onNavigate: (tab: string, assetId: string) => void;
  onDelete: (e: React.MouseEvent, assetId: string) => void;
  onTrashAction: (e: React.MouseEvent, assetId: string) => void;
  onClick: (e: React.MouseEvent) => void;
  onPreviewRendered?: (assetId: string) => void;
}) {
  const [isRendering, setIsRendering] = useState(false);
  const hasMesh = "mesh" in asset.steps && asset.steps.mesh?.file;
  const hasRigging = "rigging" in asset.steps && asset.steps.rigging?.file;

  if (isTrashView) return null;

  if (!hasMesh && !hasRigging) return null;

  const handleRenderPreview = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsRendering(true);
    try {
      await renderAssetPreview(asset.asset_id);
      onPreviewRendered?.(asset.asset_id);
    } catch {
      // Fehler stumm ignorieren — Blender könnte nicht verfügbar sein
    } finally {
      setIsRendering(false);
    }
  };

  return (
    <div className="asset-card__actions" onClick={onClick}>
      {hasMesh && (
        <>
          <button
            type="button"
            className="btn btn--outline btn--sm"
            onClick={handleRenderPreview}
            disabled={isRendering}
            title="Vorschau-PNG rendern (Blender)"
          >
            {isRendering ? "Rendert…" : "Vorschau"}
          </button>
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

export interface AssetGridProps {
  displayAssets: AssetListItem[];
  baseUrl: string;
  selectMode: boolean;
  showTrash: boolean;
  selectedIds: Set<string>;
  toggleSelect: (assetId: string) => void;
  handleDeleteClick: (e: React.MouseEvent, assetId: string) => void;
  handleTrashActionClick: (e: React.MouseEvent, assetId: string) => void;
  handleNavigateToPipeline: (tab: string, assetId: string) => void;
  handleRateAsset: (assetId: string, rating: number) => void;
  handleToggleFavorit: (assetId: string, favorited: boolean) => void;
  setSelectedAssetId: (id: string) => void;
  setTrashActionAsset: (asset: AssetListItem) => void;
  onPreviewRendered?: (assetId: string) => void;
}

export function AssetGrid({
  displayAssets,
  baseUrl,
  selectMode,
  showTrash,
  selectedIds,
  toggleSelect,
  handleDeleteClick,
  handleTrashActionClick,
  handleNavigateToPipeline,
  handleRateAsset,
  handleToggleFavorit,
  setSelectedAssetId,
  setTrashActionAsset,
  onPreviewRendered,
}: AssetGridProps) {
  if (displayAssets.length === 0) return null;

  return (
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
                <div className="asset-card__bottom-row">
                  <StepBadges steps={asset.steps} />
                  <QualityBadge qualityGate={asset.quality_gate} />
                </div>
              </div>
            </button>
            <AssetCardActions
              asset={asset}
              isTrashView={isDeleted}
              onNavigate={handleNavigateToPipeline}
              onDelete={handleDeleteClick}
              onTrashAction={handleTrashActionClick}
              onClick={(e) => e.stopPropagation()}
              onPreviewRendered={onPreviewRendered}
            />
          </div>
        );
      })}
    </div>
  );
}

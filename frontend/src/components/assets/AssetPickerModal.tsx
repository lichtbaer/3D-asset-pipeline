import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAssets } from "../../api/assets.js";
import type { AssetListItem } from "../../api/assets.js";
import { useFocusTrap } from "../../hooks/useFocusTrap.js";
import { useEscapeKey } from "../../hooks/useEscapeKey.js";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock.js";

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
  const hasMesh = "mesh" in steps;
  const hasRigging = "rigging" in steps;
  const hasAnimation = "animation" in steps;
  return (
    <span className="asset-picker__badges">
      {hasMesh && <span title="Mesh">🧊</span>}
      {hasRigging && <span title="Rigging">🦴</span>}
      {hasAnimation && <span title="Animation">🎬</span>}
    </span>
  );
}

export type AssetPickerFilter = "has_mesh" | "has_rigging";

function filterAssets(
  assets: AssetListItem[],
  filter: AssetPickerFilter
): AssetListItem[] {
  if (filter === "has_mesh") {
    return assets.filter((a) => "mesh" in a.steps && a.steps.mesh?.file);
  }
  if (filter === "has_rigging") {
    return assets.filter((a) => "rigging" in a.steps && a.steps.rigging?.file);
  }
  return assets;
}

export interface AssetPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (asset: AssetListItem) => void;
  filter: AssetPickerFilter;
}

export function AssetPickerModal({
  isOpen,
  onClose,
  onSelect,
  filter,
}: AssetPickerModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  const { data: assets, isLoading } = useQuery({
    queryKey: ["assets"],
    queryFn: () => listAssets(),
    enabled: isOpen,
  });

  useFocusTrap(modalRef, isOpen);
  useEscapeKey(onClose, isOpen);
  useBodyScrollLock(isOpen);

  const filteredAssets = assets ? filterAssets(assets, filter) : [];
  const baseUrl =
    import.meta.env.VITE_API_URL || "http://localhost:8000";

  if (!isOpen) return null;

  return (
    <div className="asset-modal" role="dialog" aria-modal="true" ref={modalRef} aria-labelledby="asset-picker-title">
      <div className="asset-modal__backdrop" onClick={onClose} />
      <div
        className="asset-modal__content asset-picker-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="asset-modal__header">
          <h2 id="asset-picker-title">Aus Bibliothek laden</h2>
          <button
            type="button"
            className="asset-modal__close"
            onClick={onClose}
            aria-label="Schließen"
          >
            ×
          </button>
        </header>

        {isLoading && (
          <div className="asset-picker__loading">
            <div className="spinner" aria-hidden />
            <p>Assets werden geladen...</p>
          </div>
        )}

        {!isLoading && filteredAssets.length === 0 && (
          <div className="asset-picker__empty">
            <p>
              {filter === "has_mesh"
                ? "Keine Assets mit Mesh gefunden."
                : "Keine Assets mit Rigging gefunden."}
            </p>
          </div>
        )}

        {!isLoading && filteredAssets.length > 0 && (
          <div className="asset-picker__grid">
            {filteredAssets.map((asset) => {
              const thumbUrl = asset.thumbnail_url
                ? `${baseUrl}${asset.thumbnail_url}`
                : null;
              return (
                <button
                  key={asset.asset_id}
                  type="button"
                  className="asset-picker__card"
                  onClick={() => {
                    onSelect(asset);
                    onClose();
                  }}
                >
                  <div className="asset-picker__thumb">
                    {thumbUrl ? (
                      <img
                        src={thumbUrl}
                        alt=""
                        className="asset-picker__img"
                      />
                    ) : (
                      <div className="asset-picker__placeholder">
                        <span>🧊</span>
                      </div>
                    )}
                  </div>
                  <p className="asset-picker__date">
                    {formatDate(asset.created_at)}
                  </p>
                  <StepBadges steps={asset.steps} />
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

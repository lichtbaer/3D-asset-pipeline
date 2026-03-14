import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSketchfabStatus,
  importFromSketchfab,
  getMySketchfabModels,
} from "../../api/sketchfab.js";
import { useFocusTrap } from "../../hooks/useFocusTrap.js";
import { useEscapeKey } from "../../hooks/useEscapeKey.js";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock.js";
import type { SketchfabModelItem } from "../../api/sketchfab.js";

interface SketchfabImportModalProps {
  onClose: () => void;
}

function formatVertexCount(n: number): string {
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  }
  return String(n);
}

export function SketchfabImportModal({ onClose }: SketchfabImportModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [urlInput, setUrlInput] = useState("");
  const [importName, setImportName] = useState("");

  const { data: sketchfabEnabled } = useQuery({
    queryKey: ["sketchfab-status"],
    queryFn: getSketchfabStatus,
  });

  const { data: myModels, isLoading: modelsLoading } = useQuery({
    queryKey: ["sketchfab-me-models"],
    queryFn: getMySketchfabModels,
    enabled: !!sketchfabEnabled?.enabled,
  });

  const urlImportMutation = useMutation({
    mutationFn: () =>
      importFromSketchfab({
        url: urlInput.trim(),
        name: importName.trim() || undefined,
      }),
    onSuccess: (res) => {
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      onClose();
      navigate(`/assets`, { state: { importedAssetId: res.asset_id } });
    },
  });

  const modelImportMutation = useMutation({
    mutationFn: (model: SketchfabModelItem) =>
      importFromSketchfab({
        url: model.url,
        name: model.name,
      }),
    onSuccess: (res) => {
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      onClose();
      navigate(`/assets`, { state: { importedAssetId: res.asset_id } });
    },
  });

  useFocusTrap(modalRef, true);
  useEscapeKey(onClose);
  useBodyScrollLock(true);

  if (!sketchfabEnabled?.enabled) {
    return null;
  }

  const handleUrlImport = () => {
    if (urlInput.trim()) {
      urlImportMutation.mutate();
    }
  };

  const handleModelImport = (model: SketchfabModelItem) => {
    if (model.is_downloadable) {
      modelImportMutation.mutate(model);
    }
  };

  return (
    <div
      ref={modalRef}
      className="asset-modal sketchfab-import-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sketchfab-import-title"
    >
      <div className="asset-modal__backdrop" onClick={onClose} />
      <div
        className="asset-modal__content sketchfab-import-modal__content"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="asset-modal__header">
          <h2 id="sketchfab-import-title">Von Sketchfab importieren</h2>
          <button
            type="button"
            className="asset-modal__close"
            onClick={onClose}
            aria-label="Schließen"
          >
            ×
          </button>
        </header>

        <div className="sketchfab-import__url">
          <label htmlFor="sketchfab-url">URL</label>
          <div className="sketchfab-import__url-row">
            <input
              id="sketchfab-url"
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://sketchfab.com/3d-models/..."
            />
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleUrlImport}
              disabled={
                !urlInput.trim() ||
                urlImportMutation.isPending
              }
            >
              {urlImportMutation.isPending ? "Importieren…" : "Importieren"}
            </button>
          </div>
          <div className="sketchfab-import__url-optional">
            <label htmlFor="sketchfab-import-name">Name (optional)</label>
            <input
              id="sketchfab-import-name"
              type="text"
              value={importName}
              onChange={(e) => setImportName(e.target.value)}
              placeholder="Purzel Scan v2"
            />
          </div>
          {urlImportMutation.isError && (
            <p className="sketchfab-import__error">
              {urlImportMutation.error instanceof Error
                ? urlImportMutation.error.message
                : "Import fehlgeschlagen"}
            </p>
          )}
        </div>

        <hr className="sketchfab-import__divider" />

        <div className="sketchfab-import__own">
          <h3>Oder aus eigenen Modellen</h3>
          {modelsLoading ? (
            <div className="sketchfab-import__loading">
              <div className="spinner" aria-hidden />
              <p>Eigene Modelle werden geladen…</p>
            </div>
          ) : myModels?.models && myModels.models.length > 0 ? (
            <ul className="sketchfab-import__model-list">
              {myModels.models.map((model) => (
                <li key={model.uid} className="sketchfab-import__model-item">
                  <div className="sketchfab-import__model-thumb">
                    {model.thumbnail_url ? (
                      <img
                        src={model.thumbnail_url}
                        alt=""
                        width={80}
                        height={80}
                      />
                    ) : (
                      <div className="sketchfab-import__model-placeholder">
                        🧊
                      </div>
                    )}
                  </div>
                  <div className="sketchfab-import__model-info">
                    <span className="sketchfab-import__model-name">
                      {model.name}
                    </span>
                    <span className="sketchfab-import__model-stats">
                      {formatVertexCount(model.vertex_count)} Vertices
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn btn--outline btn--sm"
                    onClick={() => handleModelImport(model)}
                    disabled={
                      !model.is_downloadable ||
                      modelImportMutation.isPending
                    }
                    title={
                      !model.is_downloadable
                        ? "Modell ist nicht zum Download freigegeben"
                        : "Importieren"
                    }
                  >
                    {modelImportMutation.isPending &&
                    modelImportMutation.variables?.uid === model.uid
                      ? "Importieren…"
                      : "Importieren"}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="sketchfab-import__empty">
              Keine eigenen Modelle gefunden.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

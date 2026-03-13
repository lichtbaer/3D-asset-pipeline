import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAsset, getAssetFileUrl } from "../../api/assets.js";
import { usePipelineStore } from "../../store/PipelineStore.js";
import { MeshViewer } from "../viewer/MeshViewer.js";

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

interface AssetStepData {
  job_id?: string;
  provider_key?: string;
  file?: string;
  prompt?: string;
  generated_at?: string | null;
  [key: string]: unknown;
}

interface AssetDetailModalProps {
  assetId: string;
  onClose: () => void;
}

export function AssetDetailModal({ assetId, onClose }: AssetDetailModalProps) {
  const navigate = useNavigate();
  const { setActiveAssetId } = usePipelineStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => getAsset(assetId),
    enabled: !!assetId,
  });

  const handleAction = (
    tab: "bgremoval" | "mesh" | "rigging",
    sourceUrl: string,
    assetIdForJob: string
  ) => {
    setActiveAssetId(assetIdForJob);
    onClose();
    navigate(`/pipeline?tab=${tab}&source=${encodeURIComponent(sourceUrl)}`);
  };

  if (!assetId) return null;

  if (isLoading && !data) {
    return (
      <div className="asset-modal" role="dialog" aria-modal="true">
        <div className="asset-modal__backdrop" onClick={onClose} />
        <div className="asset-modal__content">
          <div className="asset-modal__loading">
            <div className="spinner" aria-hidden />
            <p>Asset wird geladen...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="asset-modal" role="dialog" aria-modal="true">
        <div className="asset-modal__backdrop" onClick={onClose} />
        <div className="asset-modal__content">
          <p className="asset-modal__error">
            Fehler beim Laden:{" "}
            {error instanceof Error ? error.message : "Unbekannter Fehler"}
          </p>
          <button type="button" onClick={onClose}>
            Schließen
          </button>
        </div>
      </div>
    );
  }

  const { steps } = data;
  const hasImage = "image" in steps && steps.image && "file" in steps.image;
  const hasBgremoval =
    "bgremoval" in steps && steps.bgremoval && "file" in steps.bgremoval;
  const hasMesh = "mesh" in steps && steps.mesh && "file" in steps.mesh;
  const hasRigging =
    "rigging" in steps && steps.rigging && "file" in steps.rigging;

  const imageFile =
    hasImage && steps.image && "file" in steps.image
      ? String(steps.image.file)
      : null;
  const bgremovalFile =
    hasBgremoval && steps.bgremoval && "file" in steps.bgremoval
      ? String(steps.bgremoval.file)
      : null;

  const imageUrl = imageFile ? getAssetFileUrl(data.asset_id, imageFile) : null;
  const bgremovalUrl = bgremovalFile
    ? getAssetFileUrl(data.asset_id, bgremovalFile)
    : null;
  const meshUrl =
    hasMesh && steps.mesh && "file" in steps.mesh
      ? getAssetFileUrl(data.asset_id, String(steps.mesh.file))
      : null;
  const riggingFile =
    hasRigging && steps.rigging && "file" in steps.rigging
      ? String(steps.rigging.file)
      : null;
  const riggingUrl = riggingFile
    ? getAssetFileUrl(data.asset_id, riggingFile)
    : null;

  return (
    <div className="asset-modal" role="dialog" aria-modal="true">
      <div className="asset-modal__backdrop" onClick={onClose} />
      <div className="asset-modal__content" onClick={(e) => e.stopPropagation()}>
        <header className="asset-modal__header">
          <h2>Asset {data.asset_id.slice(0, 8)}…</h2>
          <button
            type="button"
            className="asset-modal__close"
            onClick={onClose}
            aria-label="Schließen"
          >
            ×
          </button>
        </header>

        <p className="asset-modal__dates">
          Erstellt: {formatDate(data.created_at)} · Aktualisiert:{" "}
          {formatDate(data.updated_at)}
        </p>

        <section className="asset-modal__files">
          <h3>Dateien</h3>
          <div className="asset-modal__previews">
            {hasImage && imageFile && (
              <div className="asset-modal__preview-item">
                <img
                  src={getAssetFileUrl(data.asset_id, imageFile)}
                  alt="Originalbild"
                  className="asset-modal__preview-img"
                />
                <p className="asset-modal__preview-label">Bild (Original)</p>
                <a
                  href={getAssetFileUrl(data.asset_id, imageFile)}
                  download
                  className="asset-modal__download"
                >
                  Download
                </a>
              </div>
            )}
            {hasBgremoval && bgremovalFile && (
              <div className="asset-modal__preview-item">
                <div className="asset-modal__checkerboard">
                  <img
                    src={getAssetFileUrl(data.asset_id, bgremovalFile)}
                    alt="Freigestellt"
                    className="asset-modal__preview-img"
                  />
                </div>
                <p className="asset-modal__preview-label">Freigestellt</p>
                <a
                  href={getAssetFileUrl(data.asset_id, bgremovalFile)}
                  download
                  className="asset-modal__download"
                >
                  Download
                </a>
              </div>
            )}
            {hasMesh && meshUrl && (
              <div className="asset-modal__preview-item">
                <MeshViewer glbUrl={meshUrl} height={450} />
                <p className="asset-modal__preview-label">mesh.glb</p>
                <a
                  href={meshUrl}
                  download
                  className="asset-modal__download"
                >
                  Download GLB
                </a>
              </div>
            )}
            {hasRigging && riggingUrl && (
              <div className="asset-modal__preview-item">
                <MeshViewer glbUrl={riggingUrl} height={450} />
                <p className="asset-modal__preview-label">rigging.glb</p>
                <a
                  href={riggingUrl}
                  download
                  className="asset-modal__download"
                >
                  Download GLB
                </a>
              </div>
            )}
          </div>
        </section>

        <section className="asset-modal__meta">
          <h3>Metadaten</h3>
          {(Object.entries(steps) as [string, AssetStepData][]).map(
            ([stepKey, stepData]) => (
              <div key={stepKey} className="asset-modal__meta-step">
                <strong>{stepKey}</strong>: Provider{" "}
                {stepData.provider_key ?? "—"},{" "}
                {stepData.prompt ? `Prompt: ${stepData.prompt}` : ""}{" "}
                {stepData.generated_at
                  ? `· ${formatDate(stepData.generated_at)}`
                  : ""}
              </div>
            )
          )}
        </section>

        <section className="asset-modal__actions">
          <h3>Pipeline-Weiterführung</h3>
          <div className="asset-modal__action-buttons">
            {hasImage && imageUrl && !hasBgremoval && (
              <button
                type="button"
                className="asset-modal__action-btn"
                onClick={() =>
                  handleAction("bgremoval", imageUrl, data.asset_id)
                }
              >
                → Freistellen
              </button>
            )}
            {(hasImage || hasBgremoval) &&
              !hasMesh &&
              (bgremovalUrl ?? imageUrl) && (
                <button
                  type="button"
                  className="asset-modal__action-btn"
                  onClick={() =>
                    handleAction(
                      "mesh",
                      bgremovalUrl ?? imageUrl ?? "",
                      data.asset_id
                    )
                  }
                >
                  → Als Mesh-Input
                </button>
              )}
            {hasMesh && !hasRigging && meshUrl && (
              <button
                type="button"
                className="asset-modal__action-btn"
                onClick={() =>
                  handleAction("rigging", meshUrl, data.asset_id)
                }
              >
                → Riggen
              </button>
            )}
            {hasImage && hasBgremoval && hasMesh && hasRigging && (
              <p className="asset-modal__all-done">
                Alle Schritte vorhanden. Nutze die Download-Links oben.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

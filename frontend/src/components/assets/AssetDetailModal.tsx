import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getAsset, getAssetFileUrl } from "../../api/assets.js";
import { usePipelineStore } from "../../store/PipelineStore.js";
import { useFocusTrap } from "../../hooks/useFocusTrap.js";
import { useEscapeKey } from "../../hooks/useEscapeKey.js";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock.js";
import { MeshViewer } from "../viewer/MeshViewer.js";
import {
  MeshProcessingPanel,
  ProcessingResultsList,
} from "./MeshProcessingPanel.js";
import { SketchfabPanel } from "./SketchfabPanel.js";

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
  motion_prompt?: string;
  generated_at?: string | null;
  [key: string]: unknown;
}

interface AssetDetailModalProps {
  assetId: string;
  onClose: () => void;
}

export function AssetDetailModal({ assetId, onClose }: AssetDetailModalProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setActiveAssetId } = usePipelineStore();

  const modalRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => getAsset(assetId),
    enabled: !!assetId,
  });

  useFocusTrap(modalRef, true);
  useEscapeKey(onClose);
  useBodyScrollLock(true);

  const handleAction = (
    tab: "bgremoval" | "mesh" | "rigging" | "animation" | "mesh-processing",
    _sourceUrl: string,
    assetIdForJob: string
  ) => {
    setActiveAssetId(assetIdForJob);
    onClose();
    navigate(`/pipeline?tab=${tab}&assetId=${encodeURIComponent(assetIdForJob)}`);
  };

  const handleUseForRigging = (url: string, assetIdForJob: string) => {
    handleAction("rigging", url, assetIdForJob);
  };

  if (!assetId) return null;

  if (isLoading && !data) {
    return (
      <div className="asset-modal" role="dialog" aria-modal="true" ref={modalRef} aria-labelledby="asset-detail-title">
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
      <div className="asset-modal" role="dialog" aria-modal="true" ref={modalRef} aria-labelledby="asset-detail-title">
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
  const hasAnimation =
    "animation" in steps && steps.animation && "file" in steps.animation;

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
  const riggedUrl =
    hasRigging && steps.rigging && "file" in steps.rigging
      ? getAssetFileUrl(data.asset_id, String(steps.rigging.file))
      : null;
  const animationFile =
    hasAnimation && steps.animation && "file" in steps.animation
      ? String(steps.animation.file)
      : null;
  const animationUrl = animationFile
    ? getAssetFileUrl(data.asset_id, animationFile)
    : null;
  const animationStep = steps.animation as AssetStepData | undefined;
  const motionPrompt = animationStep?.prompt ?? animationStep?.motion_prompt;

  return (
    <div className="asset-modal" role="dialog" aria-modal="true" ref={modalRef} aria-labelledby="asset-detail-title">
      <div className="asset-modal__backdrop" onClick={onClose} />
      <div className="asset-modal__content" onClick={(e) => e.stopPropagation()}>
        <header className="asset-modal__header">
          <h2 id="asset-detail-title">Asset {data.asset_id.slice(0, 8)}…</h2>
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
            {hasRigging && riggedUrl && (
              <div className="asset-modal__preview-item">
                <MeshViewer glbUrl={riggedUrl} height={450} />
                <p className="asset-modal__preview-label">mesh_rigged.glb</p>
                <a
                  href={riggedUrl}
                  download
                  className="asset-modal__download"
                >
                  Download rigged GLB
                </a>
              </div>
            )}
            {hasAnimation && animationUrl && (
              <div className="asset-modal__preview-item">
                <p className="asset-modal__preview-label">🎬 Animation</p>
                {motionPrompt && (
                  <p className="asset-modal__motion-prompt">
                    Motion: {motionPrompt}
                  </p>
                )}
                <a
                  href={animationUrl}
                  download
                  className="asset-modal__download"
                >
                  Download {animationFile ?? "Animation"}
                </a>
              </div>
            )}
          </div>
        </section>

        {hasMesh && (
          <>
            <MeshProcessingPanel assetId={data.asset_id} />
            <SketchfabPanel
              assetId={data.asset_id}
              assetName={`Asset ${data.asset_id.slice(0, 8)}`}
              sketchfabUpload={data.sketchfab_upload}
              onAssetUpdate={() => {
                void queryClient.invalidateQueries({
                  queryKey: ["asset", assetId],
                });
              }}
            />
            {data.processing && data.processing.length > 0 && (
              <ProcessingResultsList
                assetId={data.asset_id}
                processing={data.processing}
                onUseForRigging={handleUseForRigging}
              />
            )}
          </>
        )}

        <section className="asset-modal__meta">
          <h3>Metadaten</h3>
          {(Object.entries(steps) as [string, AssetStepData][]).map(
            ([stepKey, stepData]) => (
              <div key={stepKey} className="asset-modal__meta-step">
                <strong>{stepKey}</strong>: Provider{" "}
                {stepData.provider_key ?? "—"},{" "}
                {(stepData.prompt || stepData.motion_prompt)
                  ? `Prompt: ${stepData.prompt ?? stepData.motion_prompt}`
                  : ""}{" "}
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
                className="btn btn--outline"
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
                  className="btn btn--outline"
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
            {hasMesh && (
              <>
                <button
                  type="button"
                  className="btn btn--outline"
                  onClick={() =>
                    handleAction("rigging", meshUrl ?? "", data.asset_id)
                  }
                >
                  → Riggen
                </button>
                <button
                  type="button"
                  className="btn btn--outline"
                  onClick={() =>
                    handleAction("mesh-processing", meshUrl ?? "", data.asset_id)
                  }
                >
                  → Mesh-Processing
                </button>
              </>
            )}
            {hasRigging && (
              <>
                <button
                  type="button"
                  className="btn btn--outline"
                  onClick={() => {
                    const glbUrl =
                      steps.rigging && "file" in steps.rigging
                        ? getAssetFileUrl(
                            data.asset_id,
                            String(steps.rigging.file)
                          )
                        : meshUrl ?? "";
                    if (glbUrl) {
                      handleAction("animation", glbUrl, data.asset_id);
                    }
                  }}
                >
                  → Animieren
                </button>
                <button
                  type="button"
                  className="btn btn--outline"
                  onClick={() =>
                    handleAction("rigging", meshUrl ?? "", data.asset_id)
                  }
                >
                  → Riggen (erneut)
                </button>
              </>
            )}
            {hasImage &&
              hasBgremoval &&
              hasMesh &&
              (hasRigging || hasAnimation) && (
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

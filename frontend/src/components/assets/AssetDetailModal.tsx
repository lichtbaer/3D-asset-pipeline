import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAsset,
  getAssetFileUrl,
  getAssetTags,
  patchAssetMeta,
  deleteAssetStep,
} from "../../api/assets.js";
import { TagSuggestionBanner } from "./TagSuggestionBanner.js";
import { usePipelineStore } from "../../store/PipelineStore.js";
import { useFocusTrap } from "../../hooks/useFocusTrap.js";
import { useEscapeKey } from "../../hooks/useEscapeKey.js";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock.js";
import { MeshViewer } from "../viewer/MeshViewer.js";
import {
  MeshProcessingPanel,
  ProcessingResultsList,
} from "./MeshProcessingPanel.js";
import { ExportPanel } from "./ExportPanel.js";
import { ImageProcessingList } from "./ImageProcessingList.js";
import { SketchfabPanel } from "./SketchfabPanel.js";
import { QualityAnalysisPanel } from "./QualityAnalysisPanel.js";
import { SavePresetModal } from "../presets/SavePresetModal.js";
import { ApplyPresetModal } from "../presets/ApplyPresetModal.js";
import { getUrlForFirstApplicableStep } from "../../utils/presetNavigation.js";

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
  onAssetUpdate?: () => void;
  /** Nach Upload: Tag-Vorschläge automatisch anzeigen. */
  initialShowTagSuggestions?: boolean;
}

export function AssetDetailModal({
  assetId,
  onClose,
  onAssetUpdate,
  initialShowTagSuggestions = false,
}: AssetDetailModalProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setActiveAssetId } = usePipelineStore();

  const modalRef = useRef<HTMLDivElement>(null);
  const exportSectionRef = useRef<HTMLElement>(null);
  const sketchfabSectionRef = useRef<HTMLElement>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => getAsset(assetId),
    enabled: !!assetId,
  });

  const { data: allTags } = useQuery({
    queryKey: ["asset-tags"],
    queryFn: getAssetTags,
    enabled: !!assetId && !!data,
  });

  const [tagInput, setTagInput] = useState("");
  const [showTagSuggestions, setShowTagSuggestions] = useState(false);
  const [showAiTagSuggestions, setShowAiTagSuggestions] =
    useState(initialShowTagSuggestions);
  const [notesInput, setNotesInput] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [showSavePreset, setShowSavePreset] = useState(false);
  const [showApplyPreset, setShowApplyPreset] = useState(false);
  const [stepDeleteModal, setStepDeleteModal] = useState<{
    step: string;
    stepLabel: string;
    affectedSteps: string[];
    message: string;
  } | null>(null);
  const lastSyncedAssetIdRef = useRef<string | null>(null);

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

  const saveMeta = async (updates: {
    name?: string | null;
    tags?: string[];
    rating?: number | null;
    notes?: string | null;
    favorited?: boolean | null;
  }) => {
    try {
      await patchAssetMeta(assetId, updates);
      void queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      onAssetUpdate?.();
    } catch {
      // Fehler ignorieren
    }
  };

  const handleStepDeleteClick = async (
    step: "image" | "bgremoval" | "mesh" | "rigging" | "animation",
    stepLabel: string
  ) => {
    try {
      const res = await deleteAssetStep(assetId, step, {
        cascade: false,
        force: false,
      });
      if (res.requires_confirmation && res.affected_steps.length > 0) {
        setStepDeleteModal({
          step,
          stepLabel,
          affectedSteps: res.affected_steps,
          message: res.message,
        });
      } else {
        void queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
        void queryClient.invalidateQueries({ queryKey: ["assets"] });
        onAssetUpdate?.();
      }
    } catch {
      // Fehler ignorieren
    }
  };

  const handleStepDeleteConfirm = async () => {
    if (!stepDeleteModal) return;
    try {
      await deleteAssetStep(assetId, stepDeleteModal.step, {
        cascade: true,
        force: true,
      });
      void queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      onAssetUpdate?.();
      setStepDeleteModal(null);
    } catch {
      setStepDeleteModal(null);
    }
  };

  const currentTags = data?.tags ?? [];
  const tagSuggestions = (allTags?.tags ?? []).filter(
    (t) =>
      t.toLowerCase().includes(tagInput.toLowerCase().trim()) &&
      !currentTags.includes(t)
  );

  const addTag = (tag: string) => {
    const t = tag.trim();
    if (t && !currentTags.includes(t)) {
      void saveMeta({ tags: [...currentTags, t] });
      setTagInput("");
      setShowTagSuggestions(false);
    }
  };

  const removeTag = (tag: string) => {
    void saveMeta({ tags: currentTags.filter((x) => x !== tag) });
  };

  useEffect(() => {
    lastSyncedAssetIdRef.current = null;
  }, [assetId]);

  useEffect(() => {
    if (initialShowTagSuggestions) {
      setShowAiTagSuggestions(true);
    }
  }, [initialShowTagSuggestions]);

  useEffect(() => {
    if (
      data &&
      data.asset_id === assetId &&
      lastSyncedAssetIdRef.current !== assetId
    ) {
      lastSyncedAssetIdRef.current = assetId;
      setNotesInput(data.notes ?? "");
      setNameInput(data.name ?? "");
    }
  }, [assetId, data]);

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
          <h2 id="asset-detail-title">
            {data.name ?? `Asset ${data.asset_id.slice(0, 8)}…`}
          </h2>
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
              <div className="asset-modal__preview-item asset-modal__step-block">
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
                <button
                  type="button"
                  className="asset-modal__step-delete"
                  onClick={() => handleStepDeleteClick("image", "Bild")}
                >
                  Step löschen
                </button>
              </div>
            )}
            {hasBgremoval && bgremovalFile && (
              <div className="asset-modal__preview-item asset-modal__step-block">
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
                <button
                  type="button"
                  className="asset-modal__step-delete"
                  onClick={() => handleStepDeleteClick("bgremoval", "Freistellung")}
                >
                  Step löschen
                </button>
              </div>
            )}
            {hasMesh && meshUrl && (
              <div className="asset-modal__preview-item asset-modal__step-block">
                <MeshViewer glbUrl={meshUrl} height={450} />
                <p className="asset-modal__preview-label">mesh.glb</p>
                <a
                  href={meshUrl}
                  download
                  className="asset-modal__download"
                >
                  Download GLB
                </a>
                <button
                  type="button"
                  className="asset-modal__step-delete"
                  onClick={() => handleStepDeleteClick("mesh", "Mesh")}
                >
                  Step löschen
                </button>
              </div>
            )}
            {hasRigging && riggedUrl && (
              <div className="asset-modal__preview-item asset-modal__step-block">
                <MeshViewer glbUrl={riggedUrl} height={450} />
                <p className="asset-modal__preview-label">mesh_rigged.glb</p>
                <a
                  href={riggedUrl}
                  download
                  className="asset-modal__download"
                >
                  Download rigged GLB
                </a>
                <button
                  type="button"
                  className="asset-modal__step-delete"
                  onClick={() => handleStepDeleteClick("rigging", "Rigging")}
                >
                  Step löschen
                </button>
              </div>
            )}
            {hasAnimation && animationUrl && (
              <div className="asset-modal__preview-item asset-modal__step-block">
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
                <button
                  type="button"
                  className="asset-modal__step-delete"
                  onClick={() => handleStepDeleteClick("animation", "Animation")}
                >
                  Step löschen
                </button>
              </div>
            )}
          </div>
          {(data.image_processing?.length ?? 0) > 0 && (
            <ImageProcessingList
              assetId={data.asset_id}
              imageProcessing={data.image_processing ?? []}
            />
          )}
        </section>

        {hasMesh && (
          <>
            <QualityAnalysisPanel
              assetId={data.asset_id}
              meshUrl={meshUrl}
              riggedUrl={riggedUrl}
              onNavigateToStep={handleAction}
              onScrollToExport={() =>
                exportSectionRef.current?.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                })
              }
              onScrollToSketchfab={() =>
                sketchfabSectionRef.current?.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                })
              }
            />
            <section ref={exportSectionRef}>
              <ExportPanel assetId={data.asset_id} />
            </section>
            <MeshProcessingPanel assetId={data.asset_id} />
            <section ref={sketchfabSectionRef}>
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
            </section>
            {data.processing && data.processing.length > 0 && (
              <ProcessingResultsList
                assetId={data.asset_id}
                processing={data.processing}
                onUseForRigging={handleUseForRigging}
              />
            )}
          </>
        )}

        <section className="asset-modal__verwaltung">
          <h3>Verwaltung</h3>
          <div className="asset-modal__verwaltung-name">
            <label className="asset-modal__verwaltung-label" htmlFor="asset-name">
              Name:
            </label>
            <input
              id="asset-name"
              type="text"
              className="asset-modal__name-input"
              placeholder="Asset-Name..."
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onBlur={(e) => {
                const v = e.target.value.trim() || null;
                void saveMeta({ name: v });
              }}
            />
          </div>
          <div className="asset-modal__verwaltung-tags">
            <label className="asset-modal__verwaltung-label">Tags:</label>
            <div className="asset-modal__tag-actions">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setShowAiTagSuggestions((v) => !v)}
                aria-pressed={showAiTagSuggestions}
              >
                🤖 Tags vorschlagen
              </button>
            </div>
            {showAiTagSuggestions && (
              <TagSuggestionBanner
                assetId={assetId}
                includeImageAnalysis={true}
                enabled={showAiTagSuggestions}
                onAssetUpdate={() => {
                  void queryClient.invalidateQueries({
                    queryKey: ["asset", assetId],
                  });
                  onAssetUpdate?.();
                }}
                onDismiss={() => setShowAiTagSuggestions(false)}
              />
            )}
            <div className="asset-modal__tag-chips">
              {currentTags.map((t) => (
                <span key={t} className="asset-modal__tag-chip">
                  {t}{" "}
                  <button
                    type="button"
                    onClick={() => removeTag(t)}
                    aria-label={`Tag ${t} entfernen`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="asset-modal__tag-input-wrap">
              <input
                type="text"
                className="asset-modal__tag-input"
                placeholder="+ Tag eingeben..."
                value={tagInput}
                onChange={(e) => {
                  setTagInput(e.target.value);
                  setShowTagSuggestions(true);
                }}
                onFocus={() => setShowTagSuggestions(true)}
                onBlur={() =>
                  setTimeout(() => setShowTagSuggestions(false), 150)
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    const v = tagInput.trim();
                    if (v) addTag(v);
                    else if (tagSuggestions[0]) addTag(tagSuggestions[0]);
                  }
                }}
              />
              {showTagSuggestions && tagSuggestions.length > 0 && (
                <ul className="asset-modal__tag-suggestions">
                  {tagSuggestions.slice(0, 8).map((t) => (
                    <li key={t}>
                      <button
                        type="button"
                        onClick={() => addTag(t)}
                      >
                        {t}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <div className="asset-modal__verwaltung-rating">
            <label className="asset-modal__verwaltung-label">Rating:</label>
            <span className="asset-modal__stars">
              {[1, 2, 3, 4, 5].map((i) => (
                <button
                  key={i}
                  type="button"
                  className="asset-modal__star"
                  onClick={() => void saveMeta({ rating: i })}
                  aria-label={`${i} Sterne`}
                >
                  {i <= (data.rating ?? 0) ? "★" : "☆"}
                </button>
              ))}
            </span>
          </div>
          <div className="asset-modal__verwaltung-notes">
            <label className="asset-modal__verwaltung-label" htmlFor="asset-notes">
              Notiz:
            </label>
            <textarea
              id="asset-notes"
              className="asset-modal__notes-input"
              placeholder="Notizen zum Asset..."
              value={notesInput}
              onChange={(e) => setNotesInput(e.target.value)}
              onBlur={(e) => {
                const v = e.target.value.trim();
                void saveMeta({ notes: v || null });
              }}
            />
          </div>
          <div className="asset-modal__verwaltung-favorit">
            <button
              type="button"
              className={`asset-modal__favorit-btn ${
                data.favorited ? "asset-modal__favorit-btn--on" : ""
              }`}
              onClick={() =>
                void saveMeta({ favorited: !(data.favorited ?? false) })
              }
            >
              {data.favorited ? "♥ Als Favorit markiert" : "♡ Als Favorit markieren"}
            </button>
          </div>
        </section>

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

        <section className="asset-modal__preset-actions">
          <button
            type="button"
            className="btn btn--outline"
            onClick={() => setShowSavePreset(true)}
          >
            💾 Als Preset speichern
          </button>
          <button
            type="button"
            className="btn btn--outline"
            onClick={() => setShowApplyPreset(true)}
          >
            ⚡ Preset anwenden
          </button>
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

      {showSavePreset && (
        <SavePresetModal
          assetId={assetId}
          onClose={() => setShowSavePreset(false)}
          onSuccess={() => {
            void queryClient.invalidateQueries({ queryKey: ["presets"] });
          }}
        />
      )}
      {showApplyPreset && (
        <ApplyPresetModal
          assetId={assetId}
          onClose={() => setShowApplyPreset(false)}
          onExecutePlan={(plan) => {
            setActiveAssetId(plan.asset_id);
            onClose();
            const url = getUrlForFirstApplicableStep(
              plan.execution_plan,
              plan.asset_id
            );
            navigate(url);
          }}
        />
      )}
      {stepDeleteModal && (
        <div
          className="asset-modal__overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="step-delete-title"
        >
          <div className="asset-modal__step-delete-dialog">
            <h3 id="step-delete-title">
              {stepDeleteModal.stepLabel}-Step löschen?
            </h3>
            <p>
              Folgende Steps werden ebenfalls gelöscht:{" "}
              {stepDeleteModal.affectedSteps.join(", ")}.
            </p>
            <p className="asset-modal__step-delete-warning">
              ⚠ {stepDeleteModal.message}
            </p>
            <div className="asset-modal__step-delete-actions">
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setStepDeleteModal(null)}
              >
                Abbrechen
              </button>
              <button
                type="button"
                className="btn btn--primary btn--danger"
                onClick={handleStepDeleteConfirm}
              >
                Alles löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

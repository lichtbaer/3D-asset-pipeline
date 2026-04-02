import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAsset,
  getAssetFileUrl,
  getAssetTags,
  patchAssetMeta,
  deleteAssetStep,
  duplicateAsset,
  type AssetStepData,
} from "../../api/assets.js";
import { useToast } from "../ui/ToastContext.js";
import { usePipelineStore } from "../../store/PipelineStore.js";
import { useFocusTrap } from "../../hooks/useFocusTrap.js";
import { useEscapeKey } from "../../hooks/useEscapeKey.js";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock.js";
import {
  MeshProcessingPanel,
  ProcessingResultsList,
} from "./MeshProcessingPanel.js";
import { ExportPanel } from "./ExportPanel.js";
import { SketchfabPanel } from "./SketchfabPanel.js";
import { QualityAnalysisPanel } from "./QualityAnalysisPanel.js";
import { SavePresetModal } from "../presets/SavePresetModal.js";
import { ApplyPresetModal } from "../presets/ApplyPresetModal.js";
import { getUrlForFirstApplicableStep } from "../../utils/presetNavigation.js";
import { AssetFilesPreviews } from "./AssetFilesPreviews.js";
import { AssetVerwaltung } from "./AssetVerwaltung.js";
import { AssetPipelineActions } from "./AssetPipelineActions.js";

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
  const { addToast } = useToast();
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
  const [isDuplicating, setIsDuplicating] = useState(false);
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
      addToast("Metadaten konnten nicht gespeichert werden.", "error");
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
      addToast("Schritt konnte nicht gelöscht werden.", "error");
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
      addToast("Schritt konnte nicht gelöscht werden.", "error");
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

  const handleDuplicate = async () => {
    setIsDuplicating(true);
    try {
      const result = await duplicateAsset(assetId);
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      addToast(`Asset dupliziert (${result.copied_steps.join(", ")}).`, "success");
      onAssetUpdate?.();
    } catch {
      addToast("Asset konnte nicht dupliziert werden.", "error");
    } finally {
      setIsDuplicating(false);
    }
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
            <p id="asset-detail-title">Asset wird geladen...</p>
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
          <p id="asset-detail-title" className="asset-modal__error">
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
          <div className="asset-modal__header-actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => void handleDuplicate()}
              disabled={isDuplicating}
              title="Asset duplizieren"
            >
              {isDuplicating ? "…" : "⎘ Duplizieren"}
            </button>
            <button
              type="button"
              className="asset-modal__close"
              onClick={onClose}
              aria-label="Schließen"
            >
              ×
            </button>
          </div>
        </header>

        <p className="asset-modal__dates">
          Erstellt: {formatDate(data.created_at)} · Aktualisiert:{" "}
          {formatDate(data.updated_at)}
        </p>

        <AssetFilesPreviews
          data={data}
          steps={steps}
          hasImage={hasImage}
          hasBgremoval={hasBgremoval}
          hasMesh={hasMesh}
          hasRigging={hasRigging}
          hasAnimation={hasAnimation}
          imageFile={imageFile}
          bgremovalFile={bgremovalFile}
          imageUrl={imageUrl}
          bgremovalUrl={bgremovalUrl}
          meshUrl={meshUrl}
          riggedUrl={riggedUrl}
          animationFile={animationFile}
          animationUrl={animationUrl}
          motionPrompt={motionPrompt}
          handleStepDeleteClick={handleStepDeleteClick}
          handleAction={handleAction}
        />

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
            <MeshProcessingPanel
              assetId={data.asset_id}
              textureBaking={data.texture_baking ?? []}
              onUseForRigging={handleUseForRigging}
            />
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

        <AssetVerwaltung
          data={data}
          currentTags={currentTags}
          allTags={allTags}
          nameInput={nameInput}
          setNameInput={setNameInput}
          notesInput={notesInput}
          setNotesInput={setNotesInput}
          saveMeta={saveMeta}
          addTag={addTag}
          removeTag={removeTag}
          tagInput={tagInput}
          setTagInput={setTagInput}
          showTagSuggestions={showTagSuggestions}
          setShowTagSuggestions={setShowTagSuggestions}
          tagSuggestions={tagSuggestions}
          showAiTagSuggestions={showAiTagSuggestions}
          setShowAiTagSuggestions={setShowAiTagSuggestions}
          assetId={assetId}
          onAssetUpdate={onAssetUpdate}
          queryClient={queryClient}
        />

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

        <AssetPipelineActions
          data={data}
          steps={steps}
          hasImage={!!hasImage}
          hasBgremoval={!!hasBgremoval}
          hasMesh={!!hasMesh}
          hasRigging={!!hasRigging}
          hasAnimation={!!hasAnimation}
          imageUrl={imageUrl}
          bgremovalUrl={bgremovalUrl}
          meshUrl={meshUrl}
          handleAction={handleAction}
        />
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

import { useState, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  listPresets,
  applyPreset,
  type Preset,
  type PresetApplyResponse,
  type ExecutionPlanItem,
} from "../../api/presets.js";
import { useFocusTrap } from "../../hooks/useFocusTrap.js";
import { useEscapeKey } from "../../hooks/useEscapeKey.js";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock.js";

const STEP_LABELS: Record<string, (item: ExecutionPlanItem) => string> = {
  image: (i) => `Bild (${i.provider ?? "—"})`,
  bgremoval: (i) => `Freistellung (${i.provider ?? "—"})`,
  mesh: (i) => `Mesh (${i.provider ?? "—"})`,
  clip_floor: () => "Boden-Clipping",
  remove_components: () => "Komponenten entfernen",
  repair: () => "Repair",
  simplify: (i) =>
    `Simplification ${i.params.target_faces ?? ""} Faces`,
  rigging: (i) => `Rigging (${i.provider ?? "—"})`,
  animation: (i) => `Animation (${i.provider ?? "—"})`,
  export: (i) => `Export ${String(i.params.format ?? "").toUpperCase()}`,
  sketchfab_upload: () => "Sketchfab-Upload",
};

function planItemLabel(item: ExecutionPlanItem): string {
  return STEP_LABELS[item.step]?.(item) ?? item.step;
}

export interface ApplyPresetModalProps {
  assetId: string;
  onClose: () => void;
  onExecutePlan: (plan: PresetApplyResponse) => void;
}

export function ApplyPresetModal({
  assetId,
  onClose,
  onExecutePlan,
}: ApplyPresetModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const [selectedPreset, setSelectedPreset] = useState<Preset | null>(null);
  const [planResult, setPlanResult] = useState<PresetApplyResponse | null>(
    null
  );

  const { data: presets, isLoading } = useQuery({
    queryKey: ["presets"],
    queryFn: listPresets,
  });

  const applyMutation = useMutation({
    mutationFn: (presetId: string) =>
      applyPreset(presetId, { asset_id: assetId }),
    onSuccess: (data) => {
      setPlanResult(data);
    },
  });

  useFocusTrap(modalRef, true);
  useEscapeKey(onClose);
  useBodyScrollLock(true);

  const handleSelectPreset = (preset: Preset) => {
    setSelectedPreset(preset);
    setPlanResult(null);
  };

  const handleGetPlan = () => {
    if (selectedPreset) {
      applyMutation.mutate(selectedPreset.id);
    }
  };

  const handleExecute = () => {
    if (planResult) {
      onExecutePlan(planResult);
      onClose();
    }
  };

  const handleBack = () => {
    setPlanResult(null);
  };

  if (!assetId) return null;

  return (
    <div
      className="asset-modal"
      role="dialog"
      aria-modal="true"
      ref={modalRef}
      aria-labelledby="apply-preset-title"
    >
      <div className="asset-modal__backdrop" onClick={onClose} />
      <div
        className="asset-modal__content preset-apply-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="asset-modal__header">
          <h2 id="apply-preset-title">
            {planResult ? "Execution-Plan" : "Preset wählen"}
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

        {planResult ? (
          <>
            <p className="preset-plan__intro">
              Execution-Plan für &quot;{selectedPreset?.name}&quot;
            </p>
            <ul className="preset-plan__list">
              {planResult.execution_plan.map((item) => (
                <li
                  key={item.step_index}
                  className={`preset-plan__item preset-plan__item--${item.status}`}
                >
                  {item.status === "skipped" ? (
                    <span className="preset-plan__check" aria-hidden>
                      ✓
                    </span>
                  ) : (
                    <span className="preset-plan__arrow" aria-hidden>
                      →
                    </span>
                  )}
                  <span className="preset-plan__label">
                    {planItemLabel(item)}
                  </span>
                  {item.reason && (
                    <span className="preset-plan__reason">
                      — {item.reason}
                    </span>
                  )}
                </li>
              ))}
            </ul>
            <div className="preset-form__actions">
              <button
                type="button"
                className="btn btn--outline"
                onClick={handleBack}
              >
                Zurück
              </button>
              <button
                type="button"
                className="btn btn--outline"
                onClick={onClose}
              >
                Abbrechen
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={handleExecute}
                disabled={planResult.steps_applicable === 0}
              >
                Plan ausführen
              </button>
            </div>
          </>
        ) : (
          <>
            {isLoading && (
              <div className="asset-modal__loading">
                <div className="spinner" aria-hidden />
                <p>Presets werden geladen...</p>
              </div>
            )}

            {!isLoading && presets && presets.length === 0 && (
              <p className="preset-form__empty">
                Keine Presets vorhanden. Erstelle zuerst ein Preset aus einem
                Asset.
              </p>
            )}

            {!isLoading && presets && presets.length > 0 && (
              <>
                <div className="preset-apply__list">
                  {presets.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      className={`preset-apply__item ${
                        selectedPreset?.id === preset.id
                          ? "preset-apply__item--selected"
                          : ""
                      }`}
                      onClick={() => handleSelectPreset(preset)}
                    >
                      <strong>{preset.name}</strong>
                      {preset.description && (
                        <span className="preset-apply__desc">
                          — {preset.description}
                        </span>
                      )}
                      <span className="preset-apply__meta">
                        {preset.steps.length} Steps
                      </span>
                    </button>
                  ))}
                </div>
                <div className="preset-form__actions">
                  <button
                    type="button"
                    className="btn btn--outline"
                    onClick={onClose}
                  >
                    Abbrechen
                  </button>
                  <button
                    type="button"
                    className="btn btn--primary"
                    onClick={handleGetPlan}
                    disabled={
                      !selectedPreset || applyMutation.isPending
                    }
                  >
                    Plan anzeigen
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

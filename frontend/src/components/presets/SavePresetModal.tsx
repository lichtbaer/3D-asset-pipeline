import { useState, useRef, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  createPreset,
  getPresetSuggestions,
  type PresetStep,
} from "../../api/presets.js";
import { useFocusTrap } from "../../hooks/useFocusTrap.js";
import { useEscapeKey } from "../../hooks/useEscapeKey.js";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock.js";

const STEP_LABELS: Record<string, (s: PresetStep) => string> = {
  image: (s) => `Bild-Generierung (${s.provider ?? "—"})`,
  bgremoval: (s) => `Freistellung (${s.provider ?? "—"})`,
  mesh: (s) => `Mesh-Generierung (${s.provider ?? "—"})`,
  clip_floor: () => "Boden-Clipping (Auto)",
  remove_components: (s) =>
    `Komponenten entfernen (${(s.params.min_component_ratio ?? 0.05) * 100}%)`,
  repair: (s) =>
    `Repair (${(s.params.operations as string[] | undefined)?.join(", ") ?? "—"})`,
  simplify: (s) =>
    `Simplification (${s.params.target_faces ?? "—"} Faces)`,
  rigging: (s) => `Rigging (${s.provider ?? "—"})`,
  animation: (s) => `Animation (${s.provider ?? "—"})`,
  export: (s) => `Export ${String(s.params.format ?? "").toUpperCase()}`,
  sketchfab_upload: () => "Sketchfab-Upload",
};

function stepLabel(step: PresetStep): string {
  return STEP_LABELS[step.step]?.(step) ?? step.step;
}

export interface SavePresetModalProps {
  assetId: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function SavePresetModal({
  assetId,
  onClose,
  onSuccess,
}: SavePresetModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const initializedRef = useRef(false);

  const { data: suggestions, isLoading } = useQuery({
    queryKey: ["preset-suggestions", assetId],
    queryFn: () => getPresetSuggestions(assetId),
    enabled: !!assetId,
  });

  const createMutation = useMutation({
    mutationFn: (payload: { name: string; description: string; steps: PresetStep[] }) =>
      createPreset(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["presets"] });
      onSuccess?.();
      onClose();
    },
  });

  useFocusTrap(modalRef, true);
  useEscapeKey(onClose);
  useBodyScrollLock(true);

  useEffect(() => {
    initializedRef.current = false;
  }, [assetId]);

  useEffect(() => {
    if (
      suggestions?.steps &&
      suggestions.steps.length > 0 &&
      !initializedRef.current
    ) {
      initializedRef.current = true;
      setSelectedIndices(new Set(suggestions.steps.map((_, i) => i)));
      setName(suggestions.suggested_name);
      setDescription(
        suggestions.steps.map((s) => stepLabel(s)).join(" → ")
      );
    }
  }, [suggestions]);

  const steps = suggestions?.steps ?? [];
  const toggleStep = (i: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const handleSubmit = () => {
    const selectedSteps = steps.filter((_, i) => selectedIndices.has(i));
    if (!name.trim() || selectedSteps.length === 0) return;
    createMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      steps: selectedSteps,
    });
  };

  if (!assetId) return null;

  return (
    <div
      className="asset-modal"
      role="dialog"
      aria-modal="true"
      ref={modalRef}
      aria-labelledby="save-preset-title"
    >
      <div className="asset-modal__backdrop" onClick={onClose} />
      <div
        className="asset-modal__content"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="asset-modal__header">
          <h2 id="save-preset-title">Preset speichern</h2>
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
          <div className="asset-modal__loading">
            <div className="spinner" aria-hidden />
            <p>Asset wird analysiert...</p>
          </div>
        )}

        {!isLoading && suggestions && (
          <>
            <div className="preset-form__field">
              <label htmlFor="preset-name">Name:</label>
              <input
                id="preset-name"
                type="text"
                className="preset-form__input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="z.B. Spiel-Charakter Standard"
              />
            </div>
            <div className="preset-form__field">
              <label htmlFor="preset-desc">Beschreibung:</label>
              <input
                id="preset-desc"
                type="text"
                className="preset-form__input"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="TRELLIS.2 → Boden-Clip → 50k → UniRig → STL"
              />
            </div>
            <div className="preset-form__steps">
              <h3>Erkannte Steps:</h3>
              <ul className="preset-form__step-list">
                {steps.map((step, i) => (
                  <li key={i} className="preset-form__step-item">
                    <label>
                      <input
                        type="checkbox"
                        checked={selectedIndices.has(i)}
                        onChange={() => toggleStep(i)}
                      />
                      {stepLabel(step)}
                    </label>
                  </li>
                ))}
              </ul>
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
                onClick={handleSubmit}
                disabled={
                  !name.trim() ||
                  selectedIndices.size === 0 ||
                  createMutation.isPending
                }
              >
                Preset speichern
              </button>
            </div>
          </>
        )}

        {!isLoading && suggestions && steps.length === 0 && (
          <p className="preset-form__empty">
            Keine Steps im Asset gefunden. Führe zuerst Pipeline-Schritte aus.
          </p>
        )}
      </div>
    </div>
  );
}

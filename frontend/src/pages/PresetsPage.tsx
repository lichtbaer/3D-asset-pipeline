import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listPresets,
  createPreset,
  updatePreset,
  deletePreset,
  type Preset,
  type PresetStep,
} from "../api/presets.js";
import { useFocusTrap } from "../hooks/useFocusTrap.js";
import { useEscapeKey } from "../hooks/useEscapeKey.js";

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

const STEP_LABELS: Record<string, (s: PresetStep) => string> = {
  image: (s) => `Bild (${s.provider ?? "—"})`,
  bgremoval: (s) => `Freistellung (${s.provider ?? "—"})`,
  mesh: (s) => `Mesh (${s.provider ?? "—"})`,
  clip_floor: () => "Boden-Clipping",
  remove_components: (s) =>
    `Komponenten (${((s.params.min_component_ratio as number) ?? 0.05) * 100}%)`,
  repair: () => "Repair",
  simplify: (s) => `Simplify ${s.params.target_faces ?? ""}`,
  rigging: (s) => `Rigging (${s.provider ?? "—"})`,
  animation: (s) => `Animation (${s.provider ?? "—"})`,
  export: (s) => `Export ${String(s.params.format ?? "").toUpperCase()}`,
  sketchfab_upload: () => "Sketchfab",
};

function stepLabel(step: PresetStep): string {
  return STEP_LABELS[step.step]?.(step) ?? step.step;
}

export function PresetsPage() {
  const queryClient = useQueryClient();
  const [editingPreset, setEditingPreset] = useState<Preset | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Preset | null>(null);

  const { data: presets, isLoading } = useQuery({
    queryKey: ["presets"],
    queryFn: listPresets,
  });

  const deleteMutation = useMutation({
    mutationFn: deletePreset,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["presets"] });
      setDeleteTarget(null);
    },
  });

  const createMutation = useMutation({
    mutationFn: createPreset,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["presets"] });
    },
  });

  const handleDuplicate = (preset: Preset) => {
    createMutation.mutate({
      name: `${preset.name} (Kopie)`,
      description: preset.description,
      steps: preset.steps,
    });
  };

  return (
    <main className="presets-page">
      <header className="presets-page__header">
        <h1>Pipeline-Presets</h1>
        <p className="presets-page__subtitle">
          Workflow-Vorlagen speichern und auf Assets anwenden
        </p>
        <div className="presets-page__actions">
          <Link to="/assets" className="presets-page__link">
            Zur Bibliothek
          </Link>
          <Link to="/pipeline" className="presets-page__link">
            Zur Pipeline
          </Link>
        </div>
      </header>

      {isLoading && (
        <div className="presets-page__loading">
          <div className="spinner" aria-hidden />
          <p>Presets werden geladen...</p>
        </div>
      )}

      {!isLoading && (!presets || presets.length === 0) && (
        <div className="presets-page__empty">
          <p>Noch keine Presets vorhanden.</p>
          <p>
            Öffne ein Asset in der Bibliothek und klicke auf &quot;Als Preset
            speichern&quot;.
          </p>
          <Link to="/assets" className="btn btn--primary">
            Zur Bibliothek
          </Link>
        </div>
      )}

      {!isLoading && presets && presets.length > 0 && (
        <div className="presets-page__grid">
          {presets.map((preset) => (
            <div key={preset.id} className="preset-card">
              <h3 className="preset-card__title">{preset.name}</h3>
              {preset.description && (
                <p className="preset-card__desc">{preset.description}</p>
              )}
              <p className="preset-card__meta">
                {preset.steps.length} Steps · {formatDate(preset.created_at)}
              </p>
              <ul className="preset-card__steps">
                {preset.steps.slice(0, 5).map((s, i) => (
                  <li key={i}>{stepLabel(s)}</li>
                ))}
                {preset.steps.length > 5 && (
                  <li>+{preset.steps.length - 5} weitere</li>
                )}
              </ul>
              <div className="preset-card__actions">
                <button
                  type="button"
                  className="btn btn--outline btn--sm"
                  onClick={() => handleDuplicate(preset)}
                  disabled={createMutation.isPending}
                >
                  Duplizieren
                </button>
                <button
                  type="button"
                  className="btn btn--outline btn--sm"
                  onClick={() => setEditingPreset(preset)}
                >
                  Bearbeiten
                </button>
                <button
                  type="button"
                  className="btn btn--outline btn--sm btn--danger"
                  onClick={() => setDeleteTarget(preset)}
                >
                  Löschen
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {deleteTarget && (
        <div
          className="delete-dialog-overlay"
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="delete-dialog"
            role="dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <h2>Preset löschen?</h2>
            <p>
              &quot;{deleteTarget.name}&quot; wird unwiderruflich gelöscht.
            </p>
            <div className="delete-dialog__actions">
              <button
                type="button"
                className="btn btn--outline"
                onClick={() => setDeleteTarget(null)}
              >
                Abbrechen
              </button>
              <button
                type="button"
                className="btn btn--primary btn--danger"
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
              >
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}

      {editingPreset && (
        <PresetEditModal
          preset={editingPreset}
          onClose={() => setEditingPreset(null)}
          onSaved={() => {
            void queryClient.invalidateQueries({ queryKey: ["presets"] });
            setEditingPreset(null);
          }}
        />
      )}
    </main>
  );
}

interface PresetEditModalProps {
  preset: Preset;
  onClose: () => void;
  onSaved: () => void;
}

function PresetEditModal({
  preset,
  onClose,
  onSaved,
}: PresetEditModalProps) {
  const [name, setName] = useState(preset.name);
  const [description, setDescription] = useState(preset.description);
  const modalRef = useRef<HTMLDivElement>(null);

  const updateMutation = useMutation({
    mutationFn: () =>
      updatePreset(preset.id, { name, description }),
    onSuccess: () => {
      onSaved();
    },
  });

  useFocusTrap(modalRef, true);
  useEscapeKey(onClose);

  return (
    <div className="asset-modal" role="dialog" ref={modalRef}>
      <div className="asset-modal__backdrop" onClick={onClose} />
      <div className="asset-modal__content" onClick={(e) => e.stopPropagation()}>
        <header className="asset-modal__header">
          <h2>Preset bearbeiten</h2>
          <button
            type="button"
            className="asset-modal__close"
            onClick={onClose}
            aria-label="Schließen"
          >
            ×
          </button>
        </header>
        <div className="preset-form__field">
          <label htmlFor="edit-name">Name:</label>
          <input
            id="edit-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="preset-form__input"
          />
        </div>
        <div className="preset-form__field">
          <label htmlFor="edit-desc">Beschreibung:</label>
          <input
            id="edit-desc"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="preset-form__input"
          />
        </div>
        <div className="preset-form__actions">
          <button type="button" className="btn btn--outline" onClick={onClose}>
            Abbrechen
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => updateMutation.mutate()}
            disabled={!name.trim() || updateMutation.isPending}
          >
            Speichern
          </button>
        </div>
      </div>
    </div>
  );
}

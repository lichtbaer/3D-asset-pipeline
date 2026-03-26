import { useState, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { MeshViewer } from "../../viewer/MeshViewer.js";
import {
  getAnimationPresets,
  type AnimationProvider,
  type MotionPreset,
} from "../../../api/animation.js";
import { InlineError } from "../../../components/ui/InlineError.js";
import { CharacterCounter } from "../../../components/ui/CharacterCounter.js";
import { Tooltip } from "../../../components/ui/Tooltip.js";
import { useFormValidation } from "../../../hooks/useFormValidation.js";

const DEFAULT_PRESETS: MotionPreset[] = [
  { key: "walk", display_name: "Gehen", prompt: "Gehen" },
  { key: "run", display_name: "Laufen", prompt: "Laufen" },
  { key: "idle", display_name: "Idle", prompt: "Idle" },
  { key: "jump", display_name: "Springen", prompt: "Springen" },
  { key: "wave", display_name: "Winken", prompt: "Winken" },
];

export interface AnimationFormProps {
  sourceGlbUrl: string;
  onSourceGlbUrlChange: (url: string) => void;
  providers: AnimationProvider[];
  providersLoading: boolean;
  onSubmit: (req: {
    source_glb_url: string;
    motion_prompt: string;
    provider_key: string;
    params?: Record<string, string | number | boolean | null>;
  }) => void;
  disabled: boolean;
}

export function AnimationForm({
  sourceGlbUrl,
  onSourceGlbUrlChange,
  providers,
  providersLoading,
  onSubmit,
  disabled,
}: AnimationFormProps) {
  const [providerKey, setProviderKey] = useState("");
  const [motionPrompt, setMotionPrompt] = useState("");

  const selectedProvider =
    providers.find((p) => p.key === providerKey) ?? providers[0];
  const effectiveProviderKey = providerKey || (selectedProvider?.key ?? "");

  const validationRules = useMemo(() => ({
    sourceGlbUrl: { validate: (v: string) => v.trim().length > 0, message: "Quell-GLB-URL ist erforderlich." },
    motionPrompt: { validate: (v: string) => v.trim().length > 0, message: "Bewegungsbeschreibung ist erforderlich." },
  }), []);
  const { touchField, getError, handleSubmitAttempt } = useFormValidation(validationRules);

  const { data: presetsData, isLoading: presetsLoading } = useQuery({
    queryKey: ["animation-presets", effectiveProviderKey],
    queryFn: () => getAnimationPresets(effectiveProviderKey),
    enabled: !!effectiveProviderKey,
  });
  const apiPresets = presetsData?.presets ?? [];
  const effectivePresets =
    apiPresets.length > 0 ? apiPresets : DEFAULT_PRESETS;

  useEffect(() => {
    if (effectiveProviderKey && !providerKey) {
      setProviderKey(effectiveProviderKey);
    }
  }, [effectiveProviderKey, providerKey]);

  const handlePresetClick = (preset: MotionPreset) => {
    setMotionPrompt(preset.prompt);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmitAttempt();
    if (!sourceGlbUrl.trim() || !effectiveProviderKey || !motionPrompt.trim())
      return;
    onSubmit({
      source_glb_url: sourceGlbUrl.trim(),
      motion_prompt: motionPrompt.trim(),
      provider_key: effectiveProviderKey,
    });
  };

  const isValid =
    sourceGlbUrl.trim().length > 0 &&
    effectiveProviderKey.length > 0 &&
    motionPrompt.trim().length > 0 &&
    !providersLoading;

  return (
    <form onSubmit={handleSubmit} className="animation-form prompt-form">
      <div className={`form-group${getError("sourceGlbUrl", sourceGlbUrl) ? " form-group--error" : ""}`}>
        <label htmlFor="animation-source-glb">Quell-GLB (rigged mesh)</label>
        <input
          id="animation-source-glb"
          type="url"
          value={sourceGlbUrl}
          onChange={(e) => onSourceGlbUrlChange(e.target.value)}
          onBlur={() => touchField("sourceGlbUrl")}
          placeholder="https://... oder /static/meshes/..."
          aria-describedby="sourceGlbUrl-error"
        />
        <InlineError message={getError("sourceGlbUrl", sourceGlbUrl)} id="sourceGlbUrl-error" />
      </div>

      {sourceGlbUrl.trim() && (
        <div className="animation-form__preview">
          <MeshViewer
            glbUrl={sourceGlbUrl}
            height={200}
            autoRotateDefault
            className="animation-form__preview-viewer"
          />
        </div>
      )}

      <div className={`form-group${getError("motionPrompt", motionPrompt) ? " form-group--error" : ""}`}>
        <label>Motion-Auswahl</label>
        <div className="animation-form__presets">
          {effectivePresets.map((preset) => (
            <button
              key={preset.key}
              type="button"
              className="animation-form__preset-btn"
              onClick={() => handlePresetClick(preset)}
              disabled={presetsLoading}
            >
              {preset.display_name}
            </button>
          ))}
        </div>
        <label htmlFor="animation-motion-prompt">
          Eigene Bewegung beschreiben
        </label>
        <CharacterCounter current={motionPrompt.trim().length} minimum={10} />
        <textarea
          id="animation-motion-prompt"
          value={motionPrompt}
          onChange={(e) => setMotionPrompt(e.target.value)}
          onBlur={() => touchField("motionPrompt")}
          placeholder="z.B. Gehen, Laufen, Idle..."
          rows={3}
          className="animation-form__textarea"
          aria-describedby="motionPrompt-error"
        />
        <InlineError message={getError("motionPrompt", motionPrompt)} id="motionPrompt-error" />
      </div>

      <div className="form-group">
        <label htmlFor="animation-provider">Provider</label>
        <select
          id="animation-provider"
          value={effectiveProviderKey}
          onChange={(e) => setProviderKey(e.target.value)}
          disabled={providersLoading}
        >
          {providersLoading ? (
            <option value="">Lade Provider...</option>
          ) : (
            providers.map((p) => (
              <option key={p.key} value={p.key}>
                {p.display_name}
              </option>
            ))
          )}
        </select>
      </div>

      {(disabled || !isValid || providersLoading) && !isValid ? (
        <Tooltip text="Bitte alle Pflichtfelder korrekt ausfüllen.">
          <button type="submit" disabled={disabled || !isValid || providersLoading}>
            Animation generieren
          </button>
        </Tooltip>
      ) : (
        <button type="submit" disabled={disabled || providersLoading}>
          Animation generieren
        </button>
      )}
    </form>
  );
}


import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { MeshViewer } from "../../viewer/MeshViewer.js";
import {
  getAnimationPresets,
  type AnimationProvider,
  type AnimationPreset,
} from "../../../api/animation.js";

const DEFAULT_PRESETS: AnimationPreset[] = [
  { key: "walk", label: "Gehen", motion_prompt: "Gehen" },
  { key: "run", label: "Laufen", motion_prompt: "Laufen" },
  { key: "idle", label: "Idle", motion_prompt: "Idle" },
  { key: "jump", label: "Springen", motion_prompt: "Springen" },
  { key: "wave", label: "Winken", motion_prompt: "Winken" },
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
    params?: Record<string, unknown>;
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

  const handlePresetClick = (preset: AnimationPreset) => {
    setMotionPrompt(preset.motion_prompt);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
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
      <div className="form-group">
        <label htmlFor="animation-source-glb">Quell-GLB (rigged mesh)</label>
        <input
          id="animation-source-glb"
          type="url"
          value={sourceGlbUrl}
          onChange={(e) => onSourceGlbUrlChange(e.target.value)}
          placeholder="https://... oder /static/meshes/..."
        />
      </div>

      {sourceGlbUrl.trim() && (
        <div className="animation-form__preview">
          <MeshViewer
            glbUrl={sourceGlbUrl}
            height={200}
            autoRotate
            className="animation-form__preview-viewer"
          />
        </div>
      )}

      <div className="form-group">
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
              {preset.label}
            </button>
          ))}
        </div>
        <label htmlFor="animation-motion-prompt">
          Eigene Bewegung beschreiben
        </label>
        <textarea
          id="animation-motion-prompt"
          value={motionPrompt}
          onChange={(e) => setMotionPrompt(e.target.value)}
          placeholder="z.B. Gehen, Laufen, Idle..."
          rows={3}
          className="animation-form__textarea"
        />
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

      <button type="submit" disabled={disabled || !isValid || providersLoading}>
        Animation generieren
      </button>
    </form>
  );
}


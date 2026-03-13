import { useState } from "react";
import type { AnimationProvider, MotionPreset } from "../../api/animation.js";

export interface AnimationFormProps {
  sourceGlbUrl: string;
  onSourceGlbUrlChange: (url: string) => void;
  providers: AnimationProvider[];
  presets: MotionPreset[];
  providersLoading: boolean;
  presetsLoading: boolean;
  onSubmit: (req: {
    source_glb_url: string;
    provider_key: string;
    motion_prompt: string;
  }) => void;
  disabled: boolean;
}

export function AnimationForm({
  sourceGlbUrl,
  onSourceGlbUrlChange,
  providers,
  presets,
  providersLoading,
  presetsLoading,
  onSubmit,
  disabled,
}: AnimationFormProps) {
  const [providerKey, setProviderKey] = useState("");
  const [motionPrompt, setMotionPrompt] = useState("");
  const selectedProvider =
    providers.find((p) => p.key === providerKey) ?? providers[0];
  const effectiveProviderKey =
    providerKey || (selectedProvider?.key ?? "");

  const handlePresetSelect = (preset: MotionPreset) => {
    setMotionPrompt(preset.prompt);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceGlbUrl.trim() || !effectiveProviderKey || !motionPrompt.trim())
      return;
    onSubmit({
      source_glb_url: sourceGlbUrl.trim(),
      provider_key: effectiveProviderKey,
      motion_prompt: motionPrompt.trim(),
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
        <label htmlFor="animation-source-url">Quell-GLB-URL</label>
        <input
          id="animation-source-url"
          type="url"
          value={sourceGlbUrl}
          onChange={(e) => onSourceGlbUrlChange(e.target.value)}
          placeholder="https://... oder /assets/.../files/mesh.glb"
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

      <div className="form-group">
        <label htmlFor="animation-motion-prompt">Motion-Prompt</label>
        <input
          id="animation-motion-prompt"
          type="text"
          value={motionPrompt}
          onChange={(e) => setMotionPrompt(e.target.value)}
          placeholder="z.B. character walking forward naturally"
        />
        {presets.length > 0 && (
          <div className="animation-form__presets">
            {presets.map((preset) => (
              <button
                key={preset.key}
                type="button"
                className="animation-form__preset-btn"
                onClick={() => handlePresetSelect(preset)}
                disabled={presetsLoading}
              >
                {preset.display_name}
              </button>
            ))}
          </div>
        )}
      </div>

      <button type="submit" disabled={disabled || !isValid || providersLoading}>
        Animieren
      </button>
    </form>
  );
}

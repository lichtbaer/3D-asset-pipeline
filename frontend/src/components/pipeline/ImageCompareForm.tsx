import { useState } from "react";
import type { ImageProvider } from "../../api/generation.js";
import type { CompareImageRequest } from "../../api/compare.js";

const SIZE_OPTIONS = [512, 768, 1024] as const;

export interface ImageCompareFormProps {
  imageProviders: ImageProvider[];
  imageProvidersLoading: boolean;
  onSubmit: (req: CompareImageRequest) => void;
  disabled: boolean;
}

export function ImageCompareForm({
  imageProviders,
  imageProvidersLoading,
  onSubmit,
  disabled,
}: ImageCompareFormProps) {
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [providerKeyA, setProviderKeyA] = useState("");
  const [providerKeyB, setProviderKeyB] = useState("");
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);

  const effectiveProviderA =
    providerKeyA || (imageProviders[0]?.key ?? "");
  const effectiveProviderB =
    providerKeyB || (imageProviders[1]?.key ?? imageProviders[0]?.key ?? "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim().length < 10) return;
    onSubmit({
      prompt: prompt.trim(),
      negative_prompt: negativePrompt.trim() || undefined,
      width,
      height,
      provider_key_a: effectiveProviderA,
      provider_key_b: effectiveProviderB,
    });
  };

  const isValid =
    prompt.trim().length >= 10 && effectiveProviderA && effectiveProviderB;

  return (
    <form onSubmit={handleSubmit} className="compare-form__form">
      <div className="form-group">
        <label htmlFor="compare-prompt">Prompt (mind. 10 Zeichen)</label>
        <textarea
          id="compare-prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Beschreibe das gewünschte Bild..."
          rows={3}
          minLength={10}
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="compare-negative-prompt">
          Negative Prompt (optional)
        </label>
        <textarea
          id="compare-negative-prompt"
          value={negativePrompt}
          onChange={(e) => setNegativePrompt(e.target.value)}
          placeholder="Was soll vermieden werden?"
          rows={2}
        />
      </div>
      <div className="compare-form__providers">
        <div className="form-group">
          <label htmlFor="compare-provider-a">Provider A</label>
          <select
            id="compare-provider-a"
            value={effectiveProviderA}
            onChange={(e) => setProviderKeyA(e.target.value)}
            disabled={imageProvidersLoading}
          >
            {imageProvidersLoading ? (
              <option value="">Lade Provider...</option>
            ) : (
              imageProviders.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.display_name}
                </option>
              ))
            )}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="compare-provider-b">Provider B</label>
          <select
            id="compare-provider-b"
            value={effectiveProviderB}
            onChange={(e) => setProviderKeyB(e.target.value)}
            disabled={imageProvidersLoading}
          >
            {imageProvidersLoading ? (
              <option value="">Lade Provider...</option>
            ) : (
              imageProviders.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.display_name}
                </option>
              ))
            )}
          </select>
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="compare-width">Breite</label>
          <select
            id="compare-width"
            value={width}
            onChange={(e) => setWidth(Number(e.target.value))}
          >
            {SIZE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="compare-height">Höhe</label>
          <select
            id="compare-height"
            value={height}
            onChange={(e) => setHeight(Number(e.target.value))}
          >
            {SIZE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>
      <button
        type="submit"
        disabled={disabled || !isValid || imageProvidersLoading}
      >
        Beide generieren
      </button>
    </form>
  );
}

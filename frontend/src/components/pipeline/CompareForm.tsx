import { useState } from "react";
import type { ImageProvider } from "../../api/generation.js";
import type { MeshProvider } from "../../api/mesh.js";
import type { CompareImageRequest, CompareMeshRequest } from "../../api/compare.js";

const SIZE_OPTIONS = [512, 768, 1024] as const;

export type CompareStep = "image" | "mesh";

export interface CompareFormProps {
  step: CompareStep;
  onStepChange: (step: CompareStep) => void;
  imageProviders: ImageProvider[];
  imageProvidersLoading: boolean;
  meshProviders: MeshProvider[];
  meshProvidersLoading: boolean;
  onImageSubmit: (req: CompareImageRequest) => void;
  onMeshSubmit: (req: CompareMeshRequest) => void;
  disabled: boolean;
}

export function CompareForm({
  step,
  onStepChange,
  imageProviders,
  imageProvidersLoading,
  meshProviders,
  meshProvidersLoading,
  onImageSubmit,
  onMeshSubmit,
  disabled,
}: CompareFormProps) {
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [providerKeyA, setProviderKeyA] = useState("");
  const [providerKeyB, setProviderKeyB] = useState("");
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);

  const [sourceImageUrl, setSourceImageUrl] = useState("");
  const [meshProviderKeyA, setMeshProviderKeyA] = useState("");
  const [meshProviderKeyB, setMeshProviderKeyB] = useState("");

  const effectiveProviderA =
    providerKeyA || (imageProviders[0]?.key ?? "");
  const effectiveProviderB =
    providerKeyB || (imageProviders[1]?.key ?? imageProviders[0]?.key ?? "");
  const effectiveMeshProviderA =
    meshProviderKeyA || (meshProviders[0]?.key ?? "");
  const effectiveMeshProviderB =
    meshProviderKeyB || (meshProviders[1]?.key ?? meshProviders[0]?.key ?? "");

  const handleImageSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim().length < 10) return;
    onImageSubmit({
      prompt: prompt.trim(),
      negative_prompt: negativePrompt.trim() || undefined,
      width,
      height,
      provider_key_a: effectiveProviderA,
      provider_key_b: effectiveProviderB,
    });
  };

  const handleMeshSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceImageUrl.trim()) return;
    onMeshSubmit({
      source_image_url: sourceImageUrl.trim(),
      provider_key_a: effectiveMeshProviderA,
      provider_key_b: effectiveMeshProviderB,
    });
  };

  const isImageValid =
    prompt.trim().length >= 10 && effectiveProviderA && effectiveProviderB;
  const isMeshValid =
    sourceImageUrl.trim().length > 0 &&
    effectiveMeshProviderA &&
    effectiveMeshProviderB;

  return (
    <div className="compare-form">
      <div className="compare-form__step-select">
        <label htmlFor="compare-step">Vergleiche:</label>
        <select
          id="compare-step"
          value={step}
          onChange={(e) => onStepChange(e.target.value as CompareStep)}
        >
          <option value="image">Bildgenerierung</option>
          <option value="mesh">Mesh-Generierung</option>
        </select>
      </div>

      {step === "image" && (
        <form onSubmit={handleImageSubmit} className="compare-form__form">
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
            disabled={disabled || !isImageValid || imageProvidersLoading}
          >
            Beide generieren
          </button>
        </form>
      )}

      {step === "mesh" && (
        <form onSubmit={handleMeshSubmit} className="compare-form__form">
          <div className="form-group">
            <label htmlFor="compare-source-url">Quellbild-URL</label>
            <input
              id="compare-source-url"
              type="url"
              value={sourceImageUrl}
              onChange={(e) => setSourceImageUrl(e.target.value)}
              placeholder="https://..."
            />
          </div>
          {sourceImageUrl.trim() && (
            <div className="mesh-form__preview">
              <img
                src={sourceImageUrl}
                alt="Quellbild"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
                className="mesh-form__preview-img"
              />
            </div>
          )}
          <div className="compare-form__providers">
            <div className="form-group">
              <label htmlFor="compare-mesh-provider-a">Provider A</label>
              <select
                id="compare-mesh-provider-a"
                value={effectiveMeshProviderA}
                onChange={(e) => setMeshProviderKeyA(e.target.value)}
                disabled={meshProvidersLoading}
              >
                {meshProvidersLoading ? (
                  <option value="">Lade Provider...</option>
                ) : (
                  meshProviders.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.display_name}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="compare-mesh-provider-b">Provider B</label>
              <select
                id="compare-mesh-provider-b"
                value={effectiveMeshProviderB}
                onChange={(e) => setMeshProviderKeyB(e.target.value)}
                disabled={meshProvidersLoading}
              >
                {meshProvidersLoading ? (
                  <option value="">Lade Provider...</option>
                ) : (
                  meshProviders.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.display_name}
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>
          <button
            type="submit"
            disabled={disabled || !isMeshValid || meshProvidersLoading}
          >
            Beide generieren
          </button>
        </form>
      )}
    </div>
  );
}

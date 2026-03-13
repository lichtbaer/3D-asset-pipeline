import { useState } from "react";
import type { MeshProvider } from "../../api/mesh.js";
import type { CompareMeshRequest } from "../../api/compare.js";

export interface MeshCompareFormProps {
  sourceImageUrl: string;
  onSourceImageUrlChange: (url: string) => void;
  meshProviders: MeshProvider[];
  meshProvidersLoading: boolean;
  onSubmit: (req: CompareMeshRequest) => void;
  disabled: boolean;
}

export function MeshCompareForm({
  sourceImageUrl,
  onSourceImageUrlChange,
  meshProviders,
  meshProvidersLoading,
  onSubmit,
  disabled,
}: MeshCompareFormProps) {
  const [meshProviderKeyA, setMeshProviderKeyA] = useState("");
  const [meshProviderKeyB, setMeshProviderKeyB] = useState("");

  const effectiveMeshProviderA =
    meshProviderKeyA || (meshProviders[0]?.key ?? "");
  const effectiveMeshProviderB =
    meshProviderKeyB || (meshProviders[1]?.key ?? meshProviders[0]?.key ?? "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceImageUrl.trim()) return;
    onSubmit({
      source_image_url: sourceImageUrl.trim(),
      provider_key_a: effectiveMeshProviderA,
      provider_key_b: effectiveMeshProviderB,
    });
  };

  const isValid =
    sourceImageUrl.trim().length > 0 &&
    effectiveMeshProviderA &&
    effectiveMeshProviderB;

  return (
    <form onSubmit={handleSubmit} className="compare-form__form">
      <div className="form-group">
        <label htmlFor="compare-source-url">Quellbild-URL</label>
        <input
          id="compare-source-url"
          type="url"
          value={sourceImageUrl}
          onChange={(e) => onSourceImageUrlChange(e.target.value)}
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
        disabled={disabled || !isValid || meshProvidersLoading}
      >
        Beide generieren
      </button>
    </form>
  );
}

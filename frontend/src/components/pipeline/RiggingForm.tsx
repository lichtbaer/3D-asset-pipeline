import { useState } from "react";
import type { RiggingProvider } from "../../api/rigging.js";

export interface RiggingFormProps {
  sourceGlbUrl: string;
  onSourceGlbUrlChange: (url: string) => void;
  providers: RiggingProvider[];
  providersLoading: boolean;
  onSubmit: (req: {
    source_glb_url: string;
    provider_key: string;
    asset_id?: string | null;
  }) => void;
  disabled: boolean;
  assetId?: string | null;
}

export function RiggingForm({
  sourceGlbUrl,
  onSourceGlbUrlChange,
  providers,
  providersLoading,
  onSubmit,
  disabled,
  assetId,
}: RiggingFormProps) {
  const [providerKey, setProviderKey] = useState("");
  const selectedProvider =
    providers.find((p) => p.key === providerKey) ?? providers[0];
  const effectiveProviderKey =
    providerKey || (selectedProvider?.key ?? "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceGlbUrl.trim() || !effectiveProviderKey) return;
    onSubmit({
      source_glb_url: sourceGlbUrl.trim(),
      provider_key: effectiveProviderKey,
      asset_id: assetId ?? null,
    });
  };

  const isValid =
    sourceGlbUrl.trim().length > 0 &&
    effectiveProviderKey.length > 0 &&
    !providersLoading;

  return (
    <form onSubmit={handleSubmit} className="rigging-form prompt-form">
      <div className="form-group">
        <label htmlFor="rigging-source-url">Quell-Mesh (GLB URL)</label>
        <input
          id="rigging-source-url"
          type="url"
          value={sourceGlbUrl}
          onChange={(e) => onSourceGlbUrlChange(e.target.value)}
          placeholder="https://.../assets/.../files/mesh.glb"
        />
      </div>

      <div className="form-group">
        <label htmlFor="rigging-provider">Provider</label>
        <select
          id="rigging-provider"
          value={effectiveProviderKey}
          onChange={(e) => setProviderKey(e.target.value)}
          disabled={providersLoading}
        >
          {providersLoading ? (
            <option value="">Lade Provider...</option>
          ) : providers.length === 0 ? (
            <option value="">Kein Provider (HF_TOKEN fehlt?)</option>
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
        Riggen
      </button>
    </form>
  );
}

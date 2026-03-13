import { useState } from "react";
import type { RiggingProvider } from "../../../api/rigging.js";
import { MeshViewer } from "../../viewer/MeshViewer.js";

export interface RiggingFormProps {
  sourceGlbUrl: string;
  onSourceGlbUrlChange: (url: string) => void;
  providers: RiggingProvider[];
  providersLoading: boolean;
  onSubmit: (req: {
    source_glb_url: string;
    provider_key: string;
    asset_id?: string;
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
    const req: {
      source_glb_url: string;
      provider_key: string;
      asset_id?: string;
    } = {
      source_glb_url: sourceGlbUrl.trim(),
      provider_key: effectiveProviderKey,
    };
    if (assetId) {
      req.asset_id = assetId;
    }
    onSubmit(req);
  };

  const isValid =
    sourceGlbUrl.trim().length > 0 &&
    effectiveProviderKey.length > 0 &&
    !providersLoading;

  return (
    <form onSubmit={handleSubmit} className="rigging-form prompt-form">
      <div className="form-group">
        <label htmlFor="rigging-source-glb">Quell-Mesh-GLB-URL</label>
        <input
          id="rigging-source-glb"
          type="url"
          value={sourceGlbUrl}
          onChange={(e) => onSourceGlbUrlChange(e.target.value)}
          placeholder="https://... oder /assets/.../files/..."
        />
      </div>

      {sourceGlbUrl.trim() && (
        <div className="rigging-form__preview">
          <MeshViewer
            glbUrl={sourceGlbUrl}
            height={200}
            autoRotateDefault
            readOnly
          />
        </div>
      )}

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
          ) : (
            providers.map((p) => (
              <option key={p.key} value={p.key}>
                {p.display_name}
              </option>
            ))
          )}
        </select>
        {effectiveProviderKey === "blender-rigify" && (
          <p className="rigging-form__hint">
            ⚡ Schnell · Kein GPU · Qualität mesh-abhängig
            <br />
            Tipp: Mesh vorher mit Open3D reparieren für bessere Ergebnisse
          </p>
        )}
      </div>

      <button type="submit" disabled={disabled || !isValid || providersLoading}>
        Riggen starten
      </button>
    </form>
  );
}

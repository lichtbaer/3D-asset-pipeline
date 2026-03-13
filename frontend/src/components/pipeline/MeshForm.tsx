import { useState, useEffect } from "react";
import type { MeshProvider } from "../../api/mesh.js";

interface ParamSchemaProperty {
  type: string;
  minimum?: number;
  maximum?: number;
  default?: string | number;
  description?: string;
}

interface ParamSchema {
  type?: string;
  properties?: Record<string, ParamSchemaProperty>;
  required?: string[];
}

export interface MeshFormProps {
  sourceImageUrl: string;
  onSourceImageUrlChange: (url: string) => void;
  providers: MeshProvider[];
  providersLoading: boolean;
  onSubmit: (req: {
    source_image_url: string;
    provider_key: string;
    params: Record<string, unknown>;
  }) => void;
  disabled: boolean;
}

function renderParamField(
  key: string,
  schema: ParamSchemaProperty,
  value: unknown,
  onChange: (key: string, value: unknown) => void
): React.ReactNode {
  if (schema.type === "integer") {
    const num = typeof value === "number" ? value : schema.default ?? schema.minimum ?? 0;
    return (
      <div key={key} className="form-group">
        <label htmlFor={`mesh-param-${key}`}>
          {schema.description ?? key}
        </label>
        <input
          id={`mesh-param-${key}`}
          type="number"
          min={schema.minimum}
          max={schema.maximum}
          value={num}
          onChange={(e) => onChange(key, Number(e.target.value))}
        />
      </div>
    );
  }
  if (schema.type === "string") {
    const str = typeof value === "string" ? value : String(schema.default ?? "");
    return (
      <div key={key} className="form-group">
        <label htmlFor={`mesh-param-${key}`}>
          {schema.description ?? key}
        </label>
        <input
          id={`mesh-param-${key}`}
          type="text"
          value={str}
          onChange={(e) => onChange(key, e.target.value)}
        />
      </div>
    );
  }
  return null;
}

export function MeshForm({
  sourceImageUrl,
  onSourceImageUrlChange,
  providers,
  providersLoading,
  onSubmit,
  disabled,
}: MeshFormProps) {
  const [providerKey, setProviderKey] = useState("");
  const [params, setParams] = useState<Record<string, unknown>>({});

  const selectedProvider = providers.find((p) => p.key === providerKey) ?? providers[0];
  const effectiveProviderKey = providerKey || (selectedProvider?.key ?? "");

  useEffect(() => {
    if (selectedProvider) {
      setParams((prev) => ({
        ...selectedProvider.default_params,
        ...prev,
      }));
    }
  }, [selectedProvider?.key]);

  const handleParamChange = (key: string, value: unknown) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceImageUrl.trim() || !effectiveProviderKey) return;
    onSubmit({
      source_image_url: sourceImageUrl.trim(),
      provider_key: effectiveProviderKey,
      params,
    });
  };

  const paramSchema = selectedProvider?.param_schema as ParamSchema | undefined;
  const properties = paramSchema?.properties ?? {};
  const isValid = sourceImageUrl.trim().length > 0 && effectiveProviderKey.length > 0;

  return (
    <form onSubmit={handleSubmit} className="mesh-form prompt-form">
      <div className="form-group">
        <label htmlFor="source-image-url">Quellbild-URL</label>
        <input
          id="source-image-url"
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

      <div className="form-group">
        <label htmlFor="mesh-provider">Provider</label>
        <select
          id="mesh-provider"
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

      {Object.entries(properties).map(([key, schema]) =>
        renderParamField(key, schema, params[key], handleParamChange)
      )}

      <button type="submit" disabled={disabled || !isValid || providersLoading}>
        Mesh generieren
      </button>
    </form>
  );
}

import { useState, useEffect, useMemo, useCallback } from "react";
import type { MeshProvider } from "../../api/mesh.js";
import type { BgRemovalProvider } from "../../api/bgremoval.js";
import type { ProviderParamValue } from "../../api/generation.js";
import { InlineError } from "../../components/ui/InlineError.js";
import { Tooltip } from "../../components/ui/Tooltip.js";
import { useFormValidation } from "../../hooks/useFormValidation.js";

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
  bgRemovalProviders?: BgRemovalProvider[];
  bgRemovalProvidersLoading?: boolean;
  onSubmit: (req: {
    source_image_url: string;
    provider_key: string;
    params: Record<string, ProviderParamValue>;
    auto_bgremoval?: boolean;
    bgremoval_provider_key?: string;
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
  bgRemovalProviders = [],
  bgRemovalProvidersLoading = false,
  onSubmit,
  disabled,
}: MeshFormProps) {
  const [providerKey, setProviderKey] = useState("");
  const [params, setParams] = useState<Record<string, ProviderParamValue>>({});
  const [autoBgRemoval, setAutoBgRemoval] = useState(false);
  const [bgRemovalProviderKey, setBgRemovalProviderKey] = useState("");

  const validationRules = useMemo(() => ({
    sourceImageUrl: { validate: (v: string) => v.trim().length > 0, message: "Quellbild-URL ist erforderlich." },
  }), []);
  const { touchField, getError, handleSubmitAttempt } = useFormValidation(validationRules);

  const selectedProvider = providers.find((p) => p.key === providerKey) ?? providers[0];
  const effectiveProviderKey = providerKey || (selectedProvider?.key ?? "");
  const selectedBgRemovalProvider =
    bgRemovalProviders.find((p) => p.key === bgRemovalProviderKey) ??
    bgRemovalProviders[0];
  const effectiveBgRemovalProviderKey =
    bgRemovalProviderKey || (selectedBgRemovalProvider?.key ?? "");

  useEffect(() => {
    if (selectedProvider) {
      setParams((prev) => ({
        ...selectedProvider.default_params,
        ...prev,
      }));
    }
  }, [selectedProvider]);

  const handleParamChange = useCallback((key: string, value: unknown) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmitAttempt();
    if (!sourceImageUrl.trim() || !effectiveProviderKey) return;
    const req: {
      source_image_url: string;
      provider_key: string;
      params: Record<string, ProviderParamValue>;
      auto_bgremoval?: boolean;
      bgremoval_provider_key?: string;
    } = {
      source_image_url: sourceImageUrl.trim(),
      provider_key: effectiveProviderKey,
      params,
    };
    if (autoBgRemoval && effectiveBgRemovalProviderKey) {
      req.auto_bgremoval = true;
      req.bgremoval_provider_key = effectiveBgRemovalProviderKey;
    }
    onSubmit(req);
  };

  const paramSchema = selectedProvider?.param_schema as ParamSchema | undefined;
  const properties = paramSchema?.properties ?? {};
  const isValid = sourceImageUrl.trim().length > 0 && effectiveProviderKey.length > 0;

  return (
    <form onSubmit={handleSubmit} className="mesh-form prompt-form">
      <div className={`form-group${getError("sourceImageUrl", sourceImageUrl) ? " form-group--error" : ""}`}>
        <label htmlFor="source-image-url">Quellbild-URL</label>
        <input
          id="source-image-url"
          type="url"
          value={sourceImageUrl}
          onChange={(e) => onSourceImageUrlChange(e.target.value)}
          onBlur={() => touchField("sourceImageUrl")}
          placeholder="https://..."
          aria-describedby="sourceImageUrl-error"
        />
        <InlineError message={getError("sourceImageUrl", sourceImageUrl)} id="sourceImageUrl-error" />
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

      {bgRemovalProviders.length > 0 && (
        <div className="form-group mesh-form__auto-bgremoval">
          <label className="mesh-form__checkbox-label">
            <input
              type="checkbox"
              checked={autoBgRemoval}
              onChange={(e) => setAutoBgRemoval(e.target.checked)}
            />
            Hintergrund vor Mesh-Generierung automatisch entfernen
          </label>
          {autoBgRemoval && (
            <div className="mesh-form__bgremoval-provider">
              <label htmlFor="mesh-bgremoval-provider">Provider:</label>
              <select
                id="mesh-bgremoval-provider"
                value={effectiveBgRemovalProviderKey}
                onChange={(e) => setBgRemovalProviderKey(e.target.value)}
                disabled={bgRemovalProvidersLoading}
              >
                {bgRemovalProvidersLoading ? (
                  <option value="">Lade Provider...</option>
                ) : (
                  bgRemovalProviders.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.display_name}
                    </option>
                  ))
                )}
              </select>
            </div>
          )}
        </div>
      )}

      {(disabled || !isValid || providersLoading) && !isValid ? (
        <Tooltip text="Bitte alle Pflichtfelder korrekt ausfüllen.">
          <button type="submit" disabled={disabled || !isValid || providersLoading}>
            Mesh generieren
          </button>
        </Tooltip>
      ) : (
        <button type="submit" disabled={disabled || providersLoading}>
          Mesh generieren
        </button>
      )}
    </form>
  );
}

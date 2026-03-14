import { useState, useMemo } from "react";
import type { BgRemovalProvider } from "../../api/bgremoval.js";
import { InlineError } from "../../components/ui/InlineError.js";
import { Tooltip } from "../../components/ui/Tooltip.js";
import { useFormValidation } from "../../hooks/useFormValidation.js";

export interface BgRemovalFormProps {
  sourceImageUrl: string;
  onSourceImageUrlChange: (url: string) => void;
  providers: BgRemovalProvider[];
  providersLoading: boolean;
  onSubmit: (req: {
    source_image_url: string;
    provider_key: string;
  }) => void;
  disabled: boolean;
}

export function BgRemovalForm({
  sourceImageUrl,
  onSourceImageUrlChange,
  providers,
  providersLoading,
  onSubmit,
  disabled,
}: BgRemovalFormProps) {
  const [providerKey, setProviderKey] = useState("");
  const selectedProvider =
    providers.find((p) => p.key === providerKey) ?? providers[0];
  const effectiveProviderKey =
    providerKey || (selectedProvider?.key ?? "");

  const validationRules = useMemo(() => ({
    sourceImageUrl: { validate: (v: string) => v.trim().length > 0, message: "Quellbild-URL ist erforderlich." },
  }), []);
  const { touchField, getError, handleSubmitAttempt } = useFormValidation(validationRules);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmitAttempt();
    if (!sourceImageUrl.trim() || !effectiveProviderKey) return;
    onSubmit({
      source_image_url: sourceImageUrl.trim(),
      provider_key: effectiveProviderKey,
    });
  };

  const isValid =
    sourceImageUrl.trim().length > 0 &&
    effectiveProviderKey.length > 0 &&
    !providersLoading;

  return (
    <form onSubmit={handleSubmit} className="bgremoval-form prompt-form">
      <div className={`form-group${getError("sourceImageUrl", sourceImageUrl) ? " form-group--error" : ""}`}>
        <label htmlFor="bgremoval-source-url">Quellbild-URL</label>
        <input
          id="bgremoval-source-url"
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
        <label htmlFor="bgremoval-provider">Provider</label>
        <select
          id="bgremoval-provider"
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
            Freistellen
          </button>
        </Tooltip>
      ) : (
        <button type="submit" disabled={disabled || providersLoading}>
          Freistellen
        </button>
      )}
    </form>
  );
}

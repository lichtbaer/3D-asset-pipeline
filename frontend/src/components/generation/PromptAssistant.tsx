import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  optimizePrompt,
  type PromptSuggestion,
  type PromptIntendedUse,
} from "../../api/promptAgent.js";

const STYLE_OPTIONS = [
  { value: "", label: "— Stil wählen —" },
  { value: "cartoon", label: "Cartoon" },
  { value: "realistic", label: "Realistisch" },
  { value: "pixel-art", label: "Pixel-Art" },
  { value: "low-poly", label: "Low-Poly" },
  { value: "stylized", label: "Stilisiert" },
] as const;

const INTENDED_USE_OPTIONS: { value: PromptIntendedUse; label: string }[] = [
  { value: "rigging", label: "Rigging" },
  { value: "mesh_only", label: "Nur Mesh" },
  { value: "3d_print", label: "3D-Druck" },
];

export interface PromptAssistantProps {
  prompt: string;
  negativePrompt: string;
  onPromptChange: (value: string) => void;
  onNegativePromptChange: (value: string) => void;
  disabled?: boolean;
}

export function PromptAssistant({
  prompt,
  negativePrompt,
  onPromptChange,
  onNegativePromptChange,
  disabled = false,
}: PromptAssistantProps) {
  const [showFromDescription, setShowFromDescription] = useState(false);
  const [description, setDescription] = useState("");
  const [style, setStyle] = useState("");
  const [intendedUse, setIntendedUse] = useState<PromptIntendedUse>("rigging");
  const [lastResult, setLastResult] = useState<PromptSuggestion | null>(null);
  const [showReasoning, setShowReasoning] = useState(false);

  const optimizeMutation = useMutation({
    mutationFn: optimizePrompt,
    onSuccess: (data: PromptSuggestion) => {
      setLastResult(data);
      setShowReasoning(false);
      onPromptChange(data.optimized_prompt);
      onNegativePromptChange(data.negative_prompt);
    },
  });

  const handleFromDescription = (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;
    optimizeMutation.mutate({
      description: description.trim(),
      style: style || undefined,
      intended_use: intendedUse,
    });
  };

  const handleOptimize = () => {
    if (!prompt.trim()) return;
    optimizeMutation.mutate({
      description: prompt.trim(),
      existing_prompt: prompt.trim(),
      intended_use: intendedUse,
      style: style || undefined,
    });
  };

  const applyVariant = (variant: string) => {
    onPromptChange(variant);
    setLastResult((prev) =>
      prev ? { ...prev, optimized_prompt: variant } : null
    );
  };

  const willOverwriteNegative = negativePrompt.trim().length > 0;

  const isLoading = optimizeMutation.isPending;
  const error = optimizeMutation.error;
  const axiosError = error && typeof error === "object" && "response" in error
    ? (error as { response?: { status?: number; data?: { message?: string } } })
    : null;

  const errorMessage = (() => {
    if (!axiosError?.response) {
      if (error) return "Netzwerkfehler oder Timeout. Bitte später erneut versuchen.";
      return null;
    }
    const res = axiosError.response;
    if (res.status === 503) {
      return "Prompt-Assistent nicht verfügbar: ANTHROPIC_API_KEY nicht gesetzt.";
    }
    if (res.status === 502) {
      return res.data?.message ?? "Fehler bei der Prompt-Optimierung. Bitte später erneut versuchen.";
    }
    if (res.status && res.status >= 400) {
      return res.data?.message ?? "Ein Fehler ist aufgetreten. Bitte später erneut versuchen.";
    }
    return null;
  })();

  return (
    <div className="prompt-assistant">
      <div className="prompt-assistant__buttons">
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => setShowFromDescription(!showFromDescription)}
          disabled={disabled || isLoading}
          aria-expanded={showFromDescription}
        >
          🤖 Aus Beschreibung
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={handleOptimize}
          disabled={disabled || isLoading || !prompt.trim()}
        >
          ✨ Optimieren
        </button>
      </div>

      {showFromDescription && (
        <form
          onSubmit={handleFromDescription}
          className="prompt-assistant__from-description"
        >
          <div className="form-group">
            <label htmlFor="prompt-desc">Kurze Beschreibung</label>
            <input
              id="prompt-desc"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="z.B. stehender Hund mit Rüstung"
              disabled={disabled || isLoading}
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="prompt-style">Stil</label>
              <select
                id="prompt-style"
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                disabled={disabled || isLoading}
              >
                {STYLE_OPTIONS.map((o) => (
                  <option key={o.value || "empty"} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="prompt-use">Verwendung</label>
              <select
                id="prompt-use"
                value={intendedUse}
                onChange={(e) =>
                  setIntendedUse(e.target.value as PromptIntendedUse)
                }
                disabled={disabled || isLoading}
              >
                {INTENDED_USE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button
            type="submit"
            className="btn btn--outline btn--sm"
            disabled={disabled || isLoading || !description.trim()}
          >
            {isLoading ? (
              <>
                <span className="spinner" aria-hidden style={{ width: 16, height: 16, borderWidth: 2 }} />
                Lädt…
              </>
            ) : (
              "Prompt generieren"
            )}
          </button>
        </form>
      )}

      {errorMessage && (
        <div className="prompt-assistant__error" role="alert">
          {errorMessage}
        </div>
      )}

      {lastResult && !errorMessage && (
        <div className="prompt-assistant__result">
          {willOverwriteNegative && (
            <p className="prompt-assistant__hint">
              Negative-Prompt wurde aktualisiert.
            </p>
          )}
          <button
            type="button"
            className="prompt-assistant__reasoning-toggle"
            onClick={() => setShowReasoning(!showReasoning)}
            aria-expanded={showReasoning}
          >
            {showReasoning ? "▼" : "▶"} Begründung & Varianten
          </button>
          {showReasoning && (
            <div className="prompt-assistant__reasoning-content">
              <p className="prompt-assistant__reasoning">{lastResult.reasoning}</p>
              {lastResult.variants.length > 0 && (
                <div className="prompt-assistant__variants">
                  <span className="prompt-assistant__variants-label">
                    Varianten:
                  </span>
                  {lastResult.variants.map((v, i) => (
                    <button
                      key={i}
                      type="button"
                      className="prompt-assistant__variant-chip"
                      onClick={() => applyVariant(v)}
                    >
                      Variante {i + 1} übernehmen
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

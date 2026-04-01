import { useState, useMemo, useEffect, useRef } from "react";
import type { GenerateImageRequest } from "../../api/generation.js";
// GenerateImageRequest ist erweitert um reference_image_url (optionales Feld)
import { InlineError } from "../../components/ui/InlineError.js";
import { CharacterCounter } from "../../components/ui/CharacterCounter.js";
import { Tooltip } from "../../components/ui/Tooltip.js";
import { PromptAssistant } from "./PromptAssistant.js";
import { useFormValidation } from "../../hooks/useFormValidation.js";
import { usePipelineStore } from "../../store/PipelineStore.js";
import { usePromptHistory } from "../../hooks/usePromptHistory.js";

const SIZE_OPTIONS = [512, 768, 1024] as const;

export interface PromptFormProps {
  models: string[];
  modelsLoading: boolean;
  onSubmit: (req: GenerateImageRequest) => void;
  disabled: boolean;
}

export function PromptForm({
  models,
  modelsLoading,
  onSubmit,
  disabled,
}: PromptFormProps) {
  const { pendingPromptFromChat, setPendingPromptFromChat } =
    usePipelineStore();
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [referenceImageUrl, setReferenceImageUrl] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const historyRef = useRef<HTMLDivElement>(null);
  const { historyItems, toggleFavorite, isFavorite } = usePromptHistory();
  const [modelKey, setModelKey] = useState("");
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);

  useEffect(() => {
    if (pendingPromptFromChat) {
      setPrompt(pendingPromptFromChat);
      setPendingPromptFromChat(null);
    }
  }, [pendingPromptFromChat, setPendingPromptFromChat]);

  const selectedModel = modelKey || (models[0] ?? "");

  const validationRules = useMemo(() => ({
    prompt: { validate: (v: string) => v.trim().length >= 10, message: "Mindestens 10 Zeichen erforderlich." },
  }), []);
  const { touchField, getError, handleSubmitAttempt } = useFormValidation(validationRules);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmitAttempt();
    if (prompt.trim().length < 10) return;
    onSubmit({
      prompt: prompt.trim(),
      provider_key: selectedModel || "picsart-default",
      width,
      height,
      negative_prompt: negativePrompt.trim() || undefined,
      reference_image_url: referenceImageUrl.trim() || undefined,
    });
  };

  const isValid = prompt.trim().length >= 10;

  return (
    <form onSubmit={handleSubmit} className="prompt-form">
      <div className={`form-group${getError("prompt", prompt) ? " form-group--error" : ""}`}>
        <div className="prompt-form__label-row">
          <label htmlFor="prompt">Prompt (mind. 10 Zeichen)</label>
          {historyItems.length > 0 && (
            <div className="prompt-form__history-wrap" ref={historyRef}>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setShowHistory((v) => !v)}
                aria-expanded={showHistory}
                aria-controls="prompt-history-dropdown"
              >
                Verlauf
              </button>
              {showHistory && (
                <div
                  id="prompt-history-dropdown"
                  className="prompt-form__history-dropdown"
                  role="listbox"
                  aria-label="Prompt-Verlauf"
                >
                  {historyItems.map((item) => (
                    <div key={item.prompt} className="prompt-form__history-item" role="option" aria-selected={false}>
                      <button
                        type="button"
                        className="prompt-form__history-text"
                        onClick={() => {
                          setPrompt(item.prompt);
                          setShowHistory(false);
                        }}
                        title={item.prompt}
                      >
                        <span className="prompt-form__history-prompt">{item.prompt.slice(0, 60)}{item.prompt.length > 60 ? "…" : ""}</span>
                        <span className="prompt-form__history-count">×{item.use_count}</span>
                      </button>
                      <button
                        type="button"
                        className={`prompt-form__history-star ${isFavorite(item.prompt) ? "prompt-form__history-star--on" : ""}`}
                        onClick={() => toggleFavorite(item.prompt)}
                        aria-label={isFavorite(item.prompt) ? "Aus Favoriten entfernen" : "Als Favorit markieren"}
                      >
                        {isFavorite(item.prompt) ? "★" : "☆"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <CharacterCounter current={prompt.trim().length} minimum={10} />
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onBlur={() => touchField("prompt")}
          placeholder="Beschreibe das gewünschte Bild..."
          rows={3}
          minLength={10}
          required
          aria-describedby="prompt-error"
        />
        <PromptAssistant
          prompt={prompt}
          negativePrompt={negativePrompt}
          onPromptChange={setPrompt}
          onNegativePromptChange={setNegativePrompt}
          disabled={disabled}
        />
        <InlineError message={getError("prompt", prompt)} id="prompt-error" />
      </div>

      <div className="form-group">
        <label htmlFor="negative-prompt">Negative Prompt (optional)</label>
        <textarea
          id="negative-prompt"
          value={negativePrompt}
          onChange={(e) => setNegativePrompt(e.target.value)}
          placeholder="Was soll vermieden werden?"
          rows={2}
        />
      </div>

      <details className="form-group prompt-form__img2img">
        <summary className="prompt-form__img2img-toggle">
          Image-to-Image (optional)
        </summary>
        <div className="form-group prompt-form__img2img-body">
          <label htmlFor="reference-image-url">Referenzbild-URL</label>
          <input
            id="reference-image-url"
            type="url"
            value={referenceImageUrl}
            onChange={(e) => setReferenceImageUrl(e.target.value)}
            placeholder="https://... (leer = reine Text-Generierung)"
            className="prompt-form__img2img-input"
          />
          {referenceImageUrl.trim() && (
            <img
              src={referenceImageUrl.trim()}
              alt="Referenzvorschau"
              className="prompt-form__img2img-preview"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
              }}
            />
          )}
        </div>
      </details>

      <div className="form-group">
        <label htmlFor="model">Modell</label>
        <select
          id="model"
          value={selectedModel}
          onChange={(e) => setModelKey(e.target.value)}
          disabled={modelsLoading}
        >
          {modelsLoading ? (
            <option value="">Lade Modelle...</option>
          ) : (
            models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))
          )}
        </select>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="width">Breite</label>
          <select
            id="width"
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
          <label htmlFor="height">Höhe</label>
          <select
            id="height"
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

      {(disabled || !isValid || modelsLoading) && !isValid ? (
        <Tooltip text="Bitte alle Pflichtfelder korrekt ausfüllen.">
          <button type="submit" className="btn btn--primary btn--lg" disabled={disabled || !isValid || modelsLoading}>
            Generieren
          </button>
        </Tooltip>
      ) : (
        <button type="submit" className="btn btn--primary btn--lg" disabled={disabled || modelsLoading}>
          Generieren
        </button>
      )}
    </form>
  );
}

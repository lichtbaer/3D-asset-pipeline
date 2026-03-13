import { useState } from "react";
import type { GenerateImageRequest } from "../../api/generation.js";

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
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [modelKey, setModelKey] = useState("");
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);

  const selectedModel = modelKey || (models[0] ?? "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim().length < 10) return;
    onSubmit({
      prompt: prompt.trim(),
      model_key: selectedModel || "picsart-default",
      width,
      height,
      negative_prompt: negativePrompt.trim() || undefined,
    });
  };

  const isValid = prompt.trim().length >= 10;

  return (
    <form onSubmit={handleSubmit} className="prompt-form">
      <div className="form-group">
        <label htmlFor="prompt">Prompt (mind. 10 Zeichen)</label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Beschreibe das gewünschte Bild..."
          rows={3}
          minLength={10}
          required
        />
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

      <button type="submit" disabled={disabled || !isValid || modelsLoading}>
        Generieren
      </button>
    </form>
  );
}

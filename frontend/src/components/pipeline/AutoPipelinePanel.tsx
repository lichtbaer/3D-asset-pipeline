/**
 * AutoPipelinePanel – One-Click Pipeline-Automatisierung.
 *
 * Ermöglicht es, alle Pipeline-Schritte (Image → BgRemoval → Mesh → Rigging → Animation)
 * mit einem Klick zu starten und den Fortschritt live zu verfolgen.
 */

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import "./AutoPipelinePanel.css";
import {
  getPipelineStreamUrl,
  startPipelineRun,
  type PipelineRunRequest,
  type PipelineRunStatus,
  type PipelineStepStatus,
} from "../../api/pipeline.js";
import { usePipelineStore } from "../../store/PipelineStore.js";

const STEP_LABELS: Record<string, string> = {
  image: "Bildgenerierung",
  bgremoval: "Background-Removal",
  mesh: "Mesh-Generierung",
  rigging: "Rigging",
  animation: "Animation",
};

const STATUS_ICONS: Record<string, string> = {
  pending: "○",
  processing: "◐",
  done: "●",
  failed: "✕",
  skipped: "—",
};

function StepIndicator({ step }: { step: PipelineStepStatus }) {
  const label = STEP_LABELS[step.step] ?? step.step;
  const icon = STATUS_ICONS[step.status] ?? "○";

  return (
    <div
      className={`auto-pipeline__step auto-pipeline__step--${step.status}`}
      aria-label={`${label}: ${step.status}`}
    >
      <span className="auto-pipeline__step-icon" aria-hidden="true">{icon}</span>
      <span className="auto-pipeline__step-label">{label}</span>
      {step.status === "processing" && (
        <span className="auto-pipeline__step-spinner" aria-label="läuft..." />
      )}
      {step.error && (
        <span className="auto-pipeline__step-error" title={step.error}>Fehler</span>
      )}
    </div>
  );
}

interface AutoPipelinePanelProps {
  /** Standard-Prompt für die Bildgenerierung */
  initialPrompt?: string;
}

export function AutoPipelinePanel({ initialPrompt = "" }: AutoPipelinePanelProps) {
  const queryClient = useQueryClient();
  const { setActiveAssetId } = usePipelineStore();

  const [prompt, setPrompt] = useState(initialPrompt);
  const [enableBgRemoval, setEnableBgRemoval] = useState(true);
  const [enableRigging, setEnableRigging] = useState(false);
  const [enableAnimation, setEnableAnimation] = useState(false);
  const [motionPrompt, setMotionPrompt] = useState("walk forward");

  const [isRunning, setIsRunning] = useState(false);
  const [runStatus, setRunStatus] = useState<PipelineRunStatus | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);

  // SSE-Stream für Pipeline-Status
  const startStreamForRun = (pipelineRunId: string) => {
    const url = getPipelineStreamUrl(pipelineRunId);
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as PipelineRunStatus;
        setRunStatus(data);

        if (data.asset_id) {
          setActiveAssetId(data.asset_id);
        }

        if (data.status === "done" || data.status === "failed") {
          es.close();
          esRef.current = null;
          setIsRunning(false);
          // Asset-Library invalidieren
          void queryClient.invalidateQueries({ queryKey: ["assets"] });
        }
      } catch {
        // Ungültige JSON ignorieren
      }
    };

    es.addEventListener("done", () => {
      es.close();
      esRef.current = null;
      setIsRunning(false);
    });

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        esRef.current = null;
        setIsRunning(false);
      }
    };
  };

  // Cleanup bei Unmount
  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isRunning) return;

    setSubmitError(null);
    setRunStatus(null);
    setIsRunning(true);

    const request: PipelineRunRequest = {
      prompt: prompt.trim(),
      enable_bgremoval: enableBgRemoval,
      enable_rigging: enableRigging,
      enable_animation: enableAnimation,
      motion_prompt: motionPrompt,
    };

    try {
      const response = await startPipelineRun(request);
      setRunStatus(response);
      startStreamForRun(response.pipeline_run_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Fehler beim Starten der Pipeline";
      setSubmitError(msg);
      setIsRunning(false);
    }
  };

  const handleReset = () => {
    esRef.current?.close();
    esRef.current = null;
    setRunStatus(null);
    setIsRunning(false);
    setSubmitError(null);
  };

  const isDone = runStatus?.status === "done";
  const isFailed = runStatus?.status === "failed";

  return (
    <div className="auto-pipeline">
      <h2 className="auto-pipeline__title">Automatische Pipeline</h2>
      <p className="auto-pipeline__desc">
        Führt alle Schritte automatisch aus: Bild generieren, Hintergrund entfernen, 3D-Mesh erstellen.
      </p>

      {!isRunning && !isDone && !isFailed && (
        <form className="auto-pipeline__form" onSubmit={handleSubmit}>
          <div className="auto-pipeline__field">
            <label htmlFor="auto-pipeline-prompt" className="auto-pipeline__label">
              Beschreibung
            </label>
            <textarea
              id="auto-pipeline-prompt"
              className="auto-pipeline__textarea"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Beschreibe das 3D-Asset, z.B. 'Ein mittelalterlicher Ritter in voller Rüstung'"
              rows={3}
              required
              disabled={isRunning}
            />
          </div>

          <fieldset className="auto-pipeline__options">
            <legend className="auto-pipeline__options-legend">Optionen</legend>

            <label className="auto-pipeline__checkbox-label">
              <input
                type="checkbox"
                checked={enableBgRemoval}
                onChange={(e) => setEnableBgRemoval(e.target.checked)}
                disabled={isRunning}
              />
              Background-Removal
            </label>

            <label className="auto-pipeline__checkbox-label">
              <input
                type="checkbox"
                checked={enableRigging}
                onChange={(e) => setEnableRigging(e.target.checked)}
                disabled={isRunning}
              />
              Rigging (Skelett)
            </label>

            <label className="auto-pipeline__checkbox-label">
              <input
                type="checkbox"
                checked={enableAnimation}
                onChange={(e) => setEnableAnimation(e.target.checked)}
                disabled={isRunning || !enableRigging}
              />
              Animation
            </label>

            {enableAnimation && enableRigging && (
              <div className="auto-pipeline__field auto-pipeline__field--indent">
                <label htmlFor="auto-pipeline-motion" className="auto-pipeline__label">
                  Bewegungs-Prompt
                </label>
                <input
                  id="auto-pipeline-motion"
                  type="text"
                  className="auto-pipeline__input"
                  value={motionPrompt}
                  onChange={(e) => setMotionPrompt(e.target.value)}
                  placeholder="z.B. walk forward, run, wave hand"
                  disabled={isRunning}
                />
              </div>
            )}
          </fieldset>

          {submitError && (
            <p className="auto-pipeline__error" role="alert">{submitError}</p>
          )}

          <button
            type="submit"
            className="btn btn--primary auto-pipeline__submit"
            disabled={!prompt.trim() || isRunning}
          >
            Pipeline starten
          </button>
        </form>
      )}

      {/* Fortschrittsanzeige */}
      {runStatus && (
        <div className="auto-pipeline__progress" aria-live="polite">
          <div className="auto-pipeline__steps">
            {runStatus.steps.map((step) => (
              <StepIndicator key={step.step} step={step} />
            ))}
          </div>

          {isRunning && (
            <p className="auto-pipeline__running-msg">Pipeline läuft...</p>
          )}

          {isDone && (
            <div className="auto-pipeline__result">
              <p className="auto-pipeline__success">
                Pipeline abgeschlossen!
                {runStatus.asset_id && (
                  <> Asset-ID: <code>{runStatus.asset_id}</code></>
                )}
              </p>
              <button
                type="button"
                className="btn btn--ghost auto-pipeline__reset"
                onClick={handleReset}
              >
                Neue Pipeline starten
              </button>
            </div>
          )}

          {isFailed && (
            <div className="auto-pipeline__result">
              <p className="auto-pipeline__error" role="alert">
                Pipeline fehlgeschlagen: {runStatus.error ?? "Unbekannter Fehler"}
              </p>
              <button
                type="button"
                className="btn btn--ghost auto-pipeline__reset"
                onClick={handleReset}
              >
                Erneut versuchen
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

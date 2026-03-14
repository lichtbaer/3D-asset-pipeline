import { useMutation } from "@tanstack/react-query";
import {
  assessQuality,
  recommendWorkflow,
  type QualityAssessment,
  type RecommendedActionType,
} from "../../api/agents.js";

const ISSUE_LABELS: Record<string, string> = {
  floor_artifact: "Boden-Artefakt",
  missing_limb: "Fehlende Gliedmaße",
  bad_topology: "Schlechte Topologie",
  not_watertight: "Nicht watertight",
  floating_geometry: "Schwebende Geometry",
  low_detail: "Zu wenig Detail",
  high_poly: "Zu viele Polygone",
  pose_issue: "Posen-Problem",
};

const SEVERITY_LABELS: Record<string, string> = {
  low: "niedrig",
  medium: "mittel",
  high: "hoch",
};

const ACTION_LABELS: Record<RecommendedActionType, string> = {
  clip_floor: "Boden abschneiden",
  repair_mesh: "Mesh reparieren",
  remove_components: "Komponenten entfernen",
  simplify: "Vereinfachen",
  rig: "Riggen",
  animate: "Animieren",
  export_stl: "Als STL exportieren",
  export_obj: "Als OBJ exportieren",
  sketchfab_upload: "Zu Sketchfab hochladen",
};

interface QualityAnalysisPanelProps {
  assetId: string;
  meshUrl: string | null;
  riggedUrl?: string | null;
  onNavigateToStep: (
    tab: "bgremoval" | "mesh" | "rigging" | "animation" | "mesh-processing",
    url: string,
    assetIdForJob: string
  ) => void;
  onScrollToExport?: () => void;
  onScrollToSketchfab?: () => void;
}

export function QualityAnalysisPanel({
  assetId,
  meshUrl,
  riggedUrl = null,
  onNavigateToStep,
  onScrollToExport,
  onScrollToSketchfab,
}: QualityAnalysisPanelProps) {
  const assessMutation = useMutation({
    mutationFn: () =>
      assessQuality({
        asset_id: assetId,
        include_mesh_analysis: true,
        include_vision: true,
      }),
  });

  const workflowMutation = useMutation({
    mutationFn: (quality: QualityAssessment | null) =>
      recommendWorkflow({
        asset_id: assetId,
        quality_assessment: quality ?? undefined,
      }),
  });

  const runAnalysis = () => {
    assessMutation.mutate(undefined, {
      onSuccess: (quality) => {
        workflowMutation.mutate(quality);
      },
    });
  };

  const quality = assessMutation.data;
  const workflow = workflowMutation.data;
  const isLoading = assessMutation.isPending || workflowMutation.isPending;
  const hasRun = quality !== undefined;

  const handleExecuteAction = (action: RecommendedActionType) => {
    const urlForMesh = meshUrl ?? "";
    const urlForAnimation = riggedUrl ?? meshUrl ?? "";
    switch (action) {
      case "clip_floor":
      case "repair_mesh":
      case "remove_components":
      case "simplify":
        onNavigateToStep("mesh-processing", urlForMesh, assetId);
        break;
      case "rig":
        onNavigateToStep("rigging", urlForMesh, assetId);
        break;
      case "animate":
        onNavigateToStep("animation", urlForAnimation, assetId);
        break;
      case "export_stl":
      case "export_obj":
        onScrollToExport?.();
        break;
      case "sketchfab_upload":
        onScrollToSketchfab?.();
        break;
    }
  };

  return (
    <section className="quality-analysis">
      <h3>KI-Analyse</h3>
      {!hasRun ? (
        <div className="quality-analysis__trigger">
          <button
            type="button"
            className="btn btn--outline"
            onClick={runAnalysis}
            disabled={isLoading}
            aria-busy={isLoading}
          >
            {isLoading ? "Analysiere…" : "🤖 Mesh analysieren"}
          </button>
        </div>
      ) : (
        <div className="quality-analysis__results">
          <div className="quality-analysis__score">
            <span className="quality-analysis__score-label">Score:</span>
            <span
              className="quality-analysis__score-stars"
              aria-label={`${quality!.score} von 10`}
            >
              {"★".repeat(quality!.score)}
              {"☆".repeat(10 - quality!.score)}
            </span>
            <span className="quality-analysis__score-value">
              {quality!.score}/10
            </span>
          </div>

          {quality!.issues.length > 0 && (
            <ul className="quality-analysis__issues">
              {quality!.issues.map((issue, i) => (
                <li
                  key={i}
                  className={`quality-analysis__issue quality-analysis__issue--${issue.severity}`}
                >
                  <span className="quality-analysis__issue-icon">
                    {issue.severity === "high" ? "⚠" : "ℹ"}
                  </span>
                  {ISSUE_LABELS[issue.type] ?? issue.type}{" "}
                  ({SEVERITY_LABELS[issue.severity] ?? issue.severity})
                  {issue.description && `: ${issue.description}`}
                </li>
              ))}
            </ul>
          )}

          <div className="quality-analysis__rigging">
            Für Rigging geeignet: {quality!.rigging_suitable ? "✓" : "✗"}
          </div>

          {quality!.recommended_actions.length > 0 && (
            <div className="quality-analysis__actions">
              <h4>Empfohlene Schritte:</h4>
              <ul>
                {quality!.recommended_actions.map((a, i) => (
                  <li key={i} className="quality-analysis__action-item">
                    <span className="quality-analysis__action-num">
                      {String.fromCharCode(0x2460 + i)}
                    </span>
                    {ACTION_LABELS[a.action] ?? a.action}{" "}
                    <button
                      type="button"
                      className="btn btn--sm btn--ghost"
                      onClick={() => handleExecuteAction(a.action)}
                    >
                      → Ausführen
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {workflow && (
            <div className="quality-analysis__next-step">
              <h4>Nächster Schritt:</h4>
              <button
                type="button"
                className="btn btn--outline btn--sm"
                onClick={() => handleExecuteAction(workflow.next_step)}
              >
                → {ACTION_LABELS[workflow.next_step] ?? workflow.next_step}
              </button>
            </div>
          )}

          {workflow?.warnings && workflow.warnings.length > 0 && (
            <ul className="quality-analysis__warnings">
              {workflow.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

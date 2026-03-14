import { apiClient } from "./client.js";

export type QualityIssueType =
  | "floor_artifact"
  | "missing_limb"
  | "bad_topology"
  | "not_watertight"
  | "floating_geometry"
  | "low_detail"
  | "high_poly"
  | "pose_issue";

export type QualityIssueSeverity = "low" | "medium" | "high";

export interface QualityIssue {
  type: QualityIssueType;
  severity: QualityIssueSeverity;
  description: string;
}

export type RecommendedActionType =
  | "clip_floor"
  | "repair_mesh"
  | "remove_components"
  | "simplify"
  | "rig"
  | "animate"
  | "export_stl"
  | "export_obj"
  | "sketchfab_upload";

export interface RecommendedAction {
  action: RecommendedActionType;
  reason: string;
  priority: number;
}

export interface QualityAssessment {
  score: number;
  issues: QualityIssue[];
  rigging_suitable: boolean;
  recommended_actions: RecommendedAction[];
}

export type WorkflowStepType = RecommendedActionType;

export interface WorkflowRecommendation {
  next_step: WorkflowStepType;
  reason: string;
  alternative_steps: WorkflowStepType[];
  warnings: string[];
}

export interface QualityAssessRequest {
  asset_id: string;
  include_mesh_analysis?: boolean;
  include_vision?: boolean;
}

export interface WorkflowRecommendRequest {
  asset_id: string;
  intention?: string | null;
  quality_assessment?: QualityAssessment | null;
}

export async function assessQuality(
  req: QualityAssessRequest
): Promise<QualityAssessment> {
  const { data } = await apiClient.post<QualityAssessment>(
    "/agents/quality/assess",
    req
  );
  return data;
}

export async function recommendWorkflow(
  req: WorkflowRecommendRequest
): Promise<WorkflowRecommendation> {
  const { data } = await apiClient.post<WorkflowRecommendation>(
    "/agents/workflow/recommend",
    req
  );
  return data;
}

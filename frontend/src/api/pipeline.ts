/**
 * API-Client für Pipeline-Automatisierung.
 * Endpoints: POST /generate/pipeline/run, GET /generate/pipeline/{id}, GET /generate/pipeline/{id}/stream
 */

import { API_BASE, apiClient } from "./client.js";

export interface PipelineRunRequest {
  prompt: string;
  image_provider_key?: string;
  image_params?: Record<string, unknown>;
  mesh_provider_key?: string;
  mesh_params?: Record<string, unknown>;
  enable_bgremoval?: boolean;
  bgremoval_provider_key?: string;
  enable_rigging?: boolean;
  rigging_provider_key?: string;
  enable_animation?: boolean;
  animation_provider_key?: string;
  motion_prompt?: string;
}

export type PipelineStepStatusValue = "pending" | "processing" | "done" | "failed" | "skipped";
export type PipelineRunStatusValue = "running" | "done" | "failed";

export interface PipelineStepStatus {
  step: string;
  job_id: string | null;
  status: PipelineStepStatusValue;
  result_url: string | null;
  error: string | null;
}

export interface PipelineRunStatus {
  pipeline_run_id: string;
  status: PipelineRunStatusValue;
  asset_id: string | null;
  steps: PipelineStepStatus[];
  created_at: string;
  updated_at: string | null;
  error: string | null;
}

export async function startPipelineRun(
  request: PipelineRunRequest
): Promise<PipelineRunStatus> {
  const { data } = await apiClient.post<PipelineRunStatus>(
    "/generate/pipeline/run",
    request
  );
  return data;
}

export async function getPipelineRunStatus(
  pipelineRunId: string
): Promise<PipelineRunStatus> {
  const { data } = await apiClient.get<PipelineRunStatus>(
    `/generate/pipeline/${pipelineRunId}`
  );
  return data;
}

/** Baut die SSE-Stream-URL für einen Pipeline-Run. */
export function getPipelineStreamUrl(pipelineRunId: string): string {
  const apiKey = import.meta.env.VITE_API_KEY as string | undefined;
  const url = `${API_BASE}/api/v1/generate/pipeline/${pipelineRunId}/stream`;
  return apiKey ? `${url}?api_key=${encodeURIComponent(apiKey)}` : url;
}

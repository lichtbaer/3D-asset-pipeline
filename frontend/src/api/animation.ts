import { apiClient } from "./client.js";

export interface AnimationProvider {
  key: string;
  display_name: string;
  default_params?: Record<string, unknown>;
  param_schema?: Record<string, unknown>;
}

export interface AnimationPreset {
  key: string;
  label: string;
  motion_prompt: string;
}

export interface AnimationGenerateRequest {
  source_glb_url: string;
  motion_prompt: string;
  provider_key: string;
  params?: Record<string, unknown>;
  asset_id?: string;
}

export type AnimationJobStatus = "pending" | "running" | "done" | "failed";

export interface AnimationJob {
  job_id: string;
  status: AnimationJobStatus;
  glb_url: string | null;
  error_msg: string | null;
  error_type: string | null;
  error_detail: string | null;
  source_glb_url: string;
  motion_prompt: string;
  provider_key: string;
  created_at: string;
  updated_at?: string;
  asset_id: string | null;
  failed_at?: string | null;
}

interface GetAnimationProvidersResponse {
  providers: AnimationProvider[];
}

interface GetAnimationPresetsResponse {
  presets: AnimationPreset[];
}

interface PostAnimationResponse {
  job_id: string;
  status: string;
}

export async function getAnimationProviders(): Promise<GetAnimationProvidersResponse> {
  const { data } = await apiClient.get<GetAnimationProvidersResponse>(
    "/generate/animation/providers"
  );
  return data;
}

export async function getAnimationPresets(
  providerKey: string
): Promise<GetAnimationPresetsResponse> {
  const { data } = await apiClient.get<GetAnimationPresetsResponse>(
    `/generate/animation/presets/${encodeURIComponent(providerKey)}`
  );
  return data;
}

export async function postGenerateAnimation(
  req: AnimationGenerateRequest
): Promise<PostAnimationResponse> {
  const { data } = await apiClient.post<PostAnimationResponse>(
    "/generate/animation",
    req
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

export async function getAnimationJobStatus(
  jobId: string
): Promise<AnimationJob> {
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const { data } = await apiClient.get<{
    job_id: string;
    status: string;
    glb_url: string | null;
    error_msg: string | null;
    error_type: string | null;
    error_detail: string | null;
    source_glb_url: string;
    motion_prompt: string;
    provider_key: string;
    created_at: string;
    updated_at?: string;
    asset_id: string | null;
    failed_at?: string | null;
  }>(`/generate/animation/${jobId}`);
  const glb_url = data.glb_url
    ? `${baseUrl}${data.glb_url}`
    : null;
  return {
    job_id: String(data.job_id),
    status: data.status as AnimationJobStatus,
    glb_url,
    error_msg: data.error_msg,
    error_type: data.error_type,
    error_detail: data.error_detail,
    source_glb_url: data.source_glb_url,
    motion_prompt: data.motion_prompt,
    provider_key: data.provider_key,
    created_at: data.created_at,
    updated_at: data.updated_at,
    asset_id: data.asset_id ? String(data.asset_id) : null,
    failed_at: data.failed_at,
  };
}

export async function retryAnimationJob(
  jobId: string
): Promise<{ job_id: string; status: string }> {
  const { data } = await apiClient.post<{ job_id: string; status: string }>(
    `/generate/animation/retry/${jobId}`
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

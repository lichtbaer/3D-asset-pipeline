import { apiClient } from "./client.js";
import { toAbsoluteUrl, createRetryFn } from "./utils.js";

export interface AnimationGenerateRequest {
  source_glb_url: string;
  provider_key: string;
  motion_prompt: string;
  asset_id?: string;
}

export type AnimationJobStatus = "pending" | "processing" | "running" | "done" | "failed";

export interface AnimationJob {
  job_id: string;
  status: AnimationJobStatus;
  animated_glb_url: string | null;
  error_msg: string | null;
  error_type: string | null;
  error_detail: string | null;
  source_glb_url: string;
  provider_key: string;
  motion_prompt: string;
  created_at: string;
  updated_at?: string;
  asset_id: string | null;
  failed_at?: string | null;
}

export interface AnimationProvider {
  key: string;
  display_name: string;
}

export interface MotionPreset {
  key: string;
  display_name: string;
  prompt: string;
}

export async function getAnimationProviders(): Promise<{
  providers: AnimationProvider[];
}> {
  const { data } = await apiClient.get<{ providers: AnimationProvider[] }>(
    "/generate/animation/providers"
  );
  return data;
}

export async function getAnimationPresets(
  providerKey: string
): Promise<{ presets: MotionPreset[] }> {
  const { data } = await apiClient.get<{ presets: MotionPreset[] }>(
    `/generate/animation/presets/${encodeURIComponent(providerKey)}`
  );
  return data;
}

export async function postGenerateAnimation(
  req: AnimationGenerateRequest
): Promise<{ job_id: string; status: string }> {
  const { data } = await apiClient.post<{ job_id: string; status: string }>(
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
  const { data } = await apiClient.get<{
    job_id: string;
    status: string;
    animated_glb_url: string | null;
    error_msg: string | null;
    error_type: string | null;
    error_detail: string | null;
    source_glb_url: string;
    provider_key: string;
    motion_prompt: string;
    created_at: string;
    updated_at?: string;
    asset_id: string | null;
    failed_at?: string | null;
  }>(`/generate/animation/${jobId}`);
  const animated_glb_url = toAbsoluteUrl(data.animated_glb_url);
  return {
    job_id: String(data.job_id),
    status: data.status as AnimationJobStatus,
    animated_glb_url,
    error_msg: data.error_msg,
    error_type: data.error_type,
    error_detail: data.error_detail,
    source_glb_url: data.source_glb_url,
    provider_key: data.provider_key,
    motion_prompt: data.motion_prompt,
    created_at: data.created_at,
    updated_at: data.updated_at,
    asset_id: data.asset_id ? String(data.asset_id) : null,
    failed_at: data.failed_at,
  };
}

export const retryAnimationJob = createRetryFn("/generate/animation");

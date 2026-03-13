import { apiClient } from "./client.js";

export interface RiggingGenerateRequest {
  source_glb_url: string;
  provider_key: string;
  asset_id?: string | null;
}

export type RiggingJobStatus = "pending" | "processing" | "done" | "failed";

export interface RiggingJob {
  job_id: string;
  status: RiggingJobStatus;
  glb_url: string | null;
  error_msg: string | null;
  error_type: string | null;
  error_detail: string | null;
  source_glb_url: string;
  provider_key: string;
  created_at: string;
  updated_at?: string;
  asset_id: string | null;
  failed_at?: string | null;
}

export interface RiggingProvider {
  key: string;
  display_name: string;
}

interface PostRiggingResponse {
  job_id: string;
  status: string;
}

interface GetRiggingProvidersResponse {
  providers: RiggingProvider[];
}

export async function postRigging(
  req: RiggingGenerateRequest
): Promise<PostRiggingResponse> {
  const { data } = await apiClient.post<PostRiggingResponse>(
    "/generate/rigging",
    req
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

export async function getRiggingJobStatus(
  jobId: string
): Promise<RiggingJob> {
  const { data } = await apiClient.get<{
    job_id: string;
    status: string;
    glb_url: string | null;
    error_msg: string | null;
    error_type: string | null;
    error_detail: string | null;
    source_glb_url: string;
    provider_key: string;
    created_at: string;
    updated_at?: string;
    asset_id: string | null;
    failed_at?: string | null;
  }>(`/generate/rigging/${jobId}`);
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const glb_url = data.glb_url
    ? data.glb_url.startsWith("http")
      ? data.glb_url
      : `${baseUrl}${data.glb_url}`
    : null;
  return {
    job_id: String(data.job_id),
    status: data.status as RiggingJobStatus,
    glb_url,
    error_msg: data.error_msg,
    error_type: data.error_type,
    error_detail: data.error_detail,
    source_glb_url: data.source_glb_url,
    provider_key: data.provider_key,
    created_at: data.created_at,
    updated_at: data.updated_at,
    asset_id: data.asset_id ? String(data.asset_id) : null,
    failed_at: data.failed_at,
  };
}

export async function retryRiggingJob(
  jobId: string
): Promise<{ job_id: string; status: string }> {
  const { data } = await apiClient.post<{ job_id: string; status: string }>(
    `/generate/rigging/retry/${jobId}`
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

export async function getRiggingProviders(): Promise<GetRiggingProvidersResponse> {
  const { data } = await apiClient.get<GetRiggingProvidersResponse>(
    "/generate/rigging/providers"
  );
  return data;
}

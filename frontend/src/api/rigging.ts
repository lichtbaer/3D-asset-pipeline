import { apiClient } from "./client.js";

export interface RiggingRequest {
  source_glb_url: string;
  provider_key: string;
  asset_id?: string;
}

export type RiggingJobStatus = "pending" | "running" | "done" | "failed";

export interface RiggingJob {
  job_id: string;
  status: RiggingJobStatus;
  provider_key: string;
  result_url: string | null;
  error_type: string | null;
  error_detail: string | null;
  asset_id: string | null;
  created_at: string;
}

export interface RiggingProvider {
  key: string;
  display_name: string;
  default_params?: Record<string, unknown>;
  param_schema?: Record<string, unknown>;
}

interface GetRiggingProvidersResponse {
  providers: RiggingProvider[];
}

export async function startRiggingJob(
  req: RiggingRequest
): Promise<{ job_id: string; status: string }> {
  const { data } = await apiClient.post<{ job_id: string; status: string }>(
    "/generate/rigging",
    req
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

export async function getRiggingJob(jobId: string): Promise<RiggingJob> {
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const { data } = await apiClient.get<{
    job_id: string;
    status: string;
    provider_key: string;
    result_url: string | null;
    error_type: string | null;
    error_detail: string | null;
    asset_id: string | null;
    created_at: string;
  }>(`/generate/rigging/${jobId}`);
  const result_url = data.result_url
    ? data.result_url.startsWith("http")
      ? data.result_url
      : `${baseUrl}${data.result_url}`
    : null;
  return {
    job_id: String(data.job_id),
    status: data.status as RiggingJobStatus,
    provider_key: data.provider_key,
    result_url,
    error_type: data.error_type ?? null,
    error_detail: data.error_detail ?? null,
    asset_id: data.asset_id ? String(data.asset_id) : null,
    created_at: data.created_at,
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

import { apiClient } from "./client.js";

export interface BgRemovalRequest {
  source_image_url: string;
  source_job_id?: string;
  provider_key: string;
}

export type BgRemovalJobStatus =
  | "pending"
  | "processing"
  | "done"
  | "failed";

export interface BgRemovalJob {
  job_id: string;
  status: BgRemovalJobStatus;
  result_url: string | null;
  error_msg: string | null;
  source_image_url: string;
  provider_key: string;
  created_at: string;
  asset_id: string | null;
}

export interface BgRemovalProvider {
  key: string;
  display_name: string;
  default_params?: Record<string, unknown>;
  param_schema: Record<string, unknown>;
}

interface PostBgRemovalResponse {
  job_id: string;
  status: string;
}

interface GetBgRemovalProvidersResponse {
  providers: BgRemovalProvider[];
}

export async function postBgRemoval(
  req: BgRemovalRequest
): Promise<PostBgRemovalResponse> {
  const { data } = await apiClient.post<PostBgRemovalResponse>(
    "/generate/bgremoval",
    req
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

export async function getBgRemovalJobStatus(
  jobId: string
): Promise<BgRemovalJob> {
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const { data } = await apiClient.get<{
    job_id: string;
    status: string;
    result_url: string | null;
    error_msg: string | null;
    source_image_url: string;
    provider_key: string;
    created_at: string;
    asset_id: string | null;
  }>(`/generate/bgremoval/${jobId}`);
  const result_url = data.result_url
    ? data.result_url.startsWith("http")
      ? data.result_url
      : `${baseUrl}${data.result_url}`
    : null;
  return {
    job_id: String(data.job_id),
    status: data.status as BgRemovalJobStatus,
    result_url,
    error_msg: data.error_msg,
    source_image_url: data.source_image_url,
    provider_key: data.provider_key,
    created_at: data.created_at,
    asset_id: data.asset_id ? String(data.asset_id) : null,
  };
}

export async function getBgRemovalProviders(): Promise<GetBgRemovalProvidersResponse> {
  const { data } = await apiClient.get<GetBgRemovalProvidersResponse>(
    "/generate/bgremoval/providers"
  );
  return data;
}

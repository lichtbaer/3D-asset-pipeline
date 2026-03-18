import { apiClient } from "./client.js";
import { toAbsoluteUrl, createRetryFn } from "./utils.js";

export interface MeshGenerationRequest {
  source_image_url: string;
  source_job_id?: string;
  provider_key: string;
  params: Record<string, unknown>;
  auto_bgremoval?: boolean;
  bgremoval_provider_key?: string;
  asset_id?: string;
}

export type MeshJobStatus = "pending" | "processing" | "done" | "failed";

export interface MeshJob {
  job_id: string;
  status: MeshJobStatus;
  glb_url: string | null;
  error_msg: string | null;
  error_type: string | null;
  error_detail: string | null;
  source_image_url: string;
  provider_key: string;
  created_at: string;
  updated_at?: string;
  asset_id: string | null;
  failed_at?: string | null;
}

export interface MeshProvider {
  key: string;
  display_name: string;
  default_params: Record<string, unknown>;
  param_schema: Record<string, unknown>;
}

interface PostGenerateMeshResponse {
  job_id: string;
  status: string;
}

interface GetMeshProvidersResponse {
  providers: MeshProvider[];
}

export async function postGenerateMesh(
  req: MeshGenerationRequest
): Promise<PostGenerateMeshResponse> {
  const { data } = await apiClient.post<PostGenerateMeshResponse>(
    "/generate/mesh",
    req
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

export async function getMeshJobStatus(jobId: string): Promise<MeshJob> {
  const { data } = await apiClient.get<{
    job_id: string;
    status: string;
    glb_url: string | null;
    error_msg: string | null;
    error_type: string | null;
    error_detail: string | null;
    source_image_url: string;
    provider_key: string;
    created_at: string;
    updated_at?: string;
    asset_id: string | null;
    failed_at?: string | null;
  }>(`/generate/mesh/${jobId}`);
  const glb_url = toAbsoluteUrl(data.glb_url);
  return {
    job_id: String(data.job_id),
    status: data.status as MeshJobStatus,
    glb_url,
    error_msg: data.error_msg,
    error_type: data.error_type,
    error_detail: data.error_detail,
    source_image_url: data.source_image_url,
    provider_key: data.provider_key,
    created_at: data.created_at,
    updated_at: data.updated_at,
    asset_id: data.asset_id ? String(data.asset_id) : null,
    failed_at: data.failed_at,
  };
}

export const retryMeshJob = createRetryFn("/generate/mesh");

export async function getMeshProviders(): Promise<GetMeshProvidersResponse> {
  const { data } = await apiClient.get<GetMeshProvidersResponse>(
    "/generate/mesh/providers"
  );
  return data;
}

import { apiClient } from "./client.js";

export interface MeshGenerationRequest {
  source_image_url: string;
  source_job_id?: string;
  provider_key: string;
  params: Record<string, unknown>;
}

export type MeshJobStatus = "pending" | "processing" | "done" | "failed";

export interface MeshJob {
  job_id: string;
  status: MeshJobStatus;
  glb_url: string | null;
  error_msg: string | null;
  source_image_url: string;
  provider_key: string;
  created_at: string;
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
    source_image_url: string;
    provider_key: string;
    created_at: string;
  }>(`/generate/mesh/${jobId}`);
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const glb_url = data.glb_url
    ? `${baseUrl}${data.glb_url}`
    : null;
  return {
    job_id: String(data.job_id),
    status: data.status as MeshJobStatus,
    glb_url,
    error_msg: data.error_msg,
    source_image_url: data.source_image_url,
    provider_key: data.provider_key,
    created_at: data.created_at,
  };
}

export async function getMeshProviders(): Promise<GetMeshProvidersResponse> {
  const { data } = await apiClient.get<GetMeshProvidersResponse>(
    "/generate/mesh/providers"
  );
  return data;
}

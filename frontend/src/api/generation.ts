import { apiClient } from "./client.js";

export interface GenerateImageRequest {
  prompt: string;
  model_key: string;
  width: number;
  height: number;
  negative_prompt?: string;
  asset_id?: string;
}

export type GenerationJobStatus = "pending" | "processing" | "done" | "failed";

export interface GenerationJob {
  job_id: string;
  status: GenerationJobStatus;
  result_url: string | null;
  error_msg: string | null;
  error_type: string | null;
  error_detail: string | null;
  provider_key: string;
  model_key: string;
  created_at: string;
  updated_at?: string;
  asset_id: string | null;
  prompt?: string | null;
  failed_at?: string | null;
}

interface PostGenerateImageResponse {
  job_id: string;
  status: string;
}

interface GetAvailableModelsResponse {
  models: string[];
}

export async function postGenerateImage(
  req: GenerateImageRequest
): Promise<PostGenerateImageResponse> {
  const { data } = await apiClient.post<PostGenerateImageResponse>(
    "/generate/image",
    req
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

export async function getJobStatus(jobId: string): Promise<GenerationJob> {
  const { data } = await apiClient.get<{
    job_id: string;
    status: string;
    result_url: string | null;
    error_msg: string | null;
    error_type: string | null;
    error_detail: string | null;
    provider_key: string;
    model_key: string;
    created_at: string;
    updated_at?: string;
    asset_id: string | null;
    prompt?: string | null;
    failed_at?: string | null;
  }>(`/generate/image/${jobId}`);
  return {
    job_id: String(data.job_id),
    status: data.status as GenerationJobStatus,
    result_url: data.result_url,
    error_msg: data.error_msg,
    error_type: data.error_type,
    error_detail: data.error_detail,
    provider_key: data.provider_key ?? data.model_key,
    model_key: data.model_key ?? data.provider_key ?? "",
    created_at: data.created_at,
    updated_at: data.updated_at,
    asset_id: data.asset_id ? String(data.asset_id) : null,
    prompt: data.prompt,
    failed_at: data.failed_at,
  };
}

export async function retryImageJob(jobId: string): Promise<{ job_id: string; status: string }> {
  const { data } = await apiClient.post<{ job_id: string; status: string }>(
    `/generate/image/retry/${jobId}`
  );
  return {
    job_id: String(data.job_id),
    status: data.status,
  };
}

export async function getAvailableModels(): Promise<GetAvailableModelsResponse> {
  const { data } = await apiClient.get<GetAvailableModelsResponse>(
    "/generate/models"
  );
  return data;
}

export interface ImageProvider {
  key: string;
  display_name: string;
  default_params: Record<string, unknown>;
  param_schema: Record<string, unknown>;
}

interface GetImageProvidersResponse {
  providers: ImageProvider[];
}

export async function getImageProviders(): Promise<GetImageProvidersResponse> {
  const { data } = await apiClient.get<GetImageProvidersResponse>(
    "/generate/image/providers"
  );
  return data;
}

import { apiClient } from "./client.js";

export interface GenerateImageRequest {
  prompt: string;
  provider_key: string;
  width: number;
  height: number;
  negative_prompt?: string;
  asset_id?: string;
  reference_image_url?: string | null;
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
  const body: Record<string, unknown> = {
    prompt: req.prompt,
    provider_key: req.provider_key,
    params: { width: req.width, height: req.height, negative_prompt: req.negative_prompt ?? null },
  };
  if (req.asset_id) body.asset_id = req.asset_id;
  if (req.reference_image_url) body.reference_image_url = req.reference_image_url;
  const { data } = await apiClient.post<PostGenerateImageResponse>("/generate/image", body);
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
    provider_key: data.provider_key,
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

/** Primitive value types accepted by provider parameters. */
export type ProviderParamValue = string | number | boolean | null;

/** A JSON-Schema-like descriptor returned by the backend for provider parameters. */
export interface ProviderParamSchema {
  type?: string;
  properties?: Record<string, {
    type: string;
    minimum?: number;
    maximum?: number;
    default?: string | number;
    description?: string;
    enum?: (string | number)[];
  }>;
  required?: string[];
  [key: string]: unknown;
}

export interface ImageProvider {
  key: string;
  display_name: string;
  default_params: Record<string, ProviderParamValue>;
  param_schema: ProviderParamSchema;
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

export interface JobListItem {
  job_id: string;
  job_type: string;
  status: GenerationJobStatus;
  provider_key: string;
  prompt: string | null;
  asset_id: string | null;
  created_at: string;
  updated_at: string | null;
  error_type: string | null;
}

export interface JobListResponse {
  jobs: JobListItem[];
  total: number;
  limit: number;
  offset: number;
}

export async function listJobs(params?: {
  status?: string;
  job_type?: string;
  limit?: number;
  offset?: number;
}): Promise<JobListResponse> {
  const { data } = await apiClient.get<JobListResponse>("/generate/jobs", { params });
  return {
    ...data,
    jobs: data.jobs.map((j) => ({
      ...j,
      job_id: String(j.job_id),
      asset_id: j.asset_id ? String(j.asset_id) : null,
      status: j.status as GenerationJobStatus,
    })),
  };
}

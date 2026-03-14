import { apiClient } from "./client.js";

export interface SketchfabStatus {
  enabled: boolean;
}

export interface SketchfabUploadRequest {
  name: string;
  description?: string;
  tags?: string[];
  is_private?: boolean;
  source_file?: string;
}

export interface SketchfabUploadResponse {
  job_id: string;
  status: string;
}

export interface SketchfabUploadStatus {
  job_id: string;
  status: string;
  sketchfab_uid?: string | null;
  sketchfab_url?: string | null;
  embed_url?: string | null;
  error_msg?: string | null;
}

export interface SketchfabImportRequest {
  url: string;
  name?: string | null;
}

export interface SketchfabImportResponse {
  asset_id: string;
}

export interface SketchfabModelItem {
  uid: string;
  name: string;
  url: string;
  thumbnail_url: string;
  vertex_count: number;
  face_count: number;
  is_downloadable: boolean;
  created_at: string;
}

export interface SketchfabMeModelsResponse {
  models: SketchfabModelItem[];
}

export async function getSketchfabStatus(): Promise<SketchfabStatus> {
  const { data } = await apiClient.get<SketchfabStatus>("/sketchfab/status");
  return data;
}

export async function uploadToSketchfab(
  assetId: string,
  body: SketchfabUploadRequest
): Promise<SketchfabUploadResponse> {
  const { data } = await apiClient.post<SketchfabUploadResponse>(
    `/assets/${assetId}/sketchfab/upload`,
    body
  );
  return data;
}

export async function getSketchfabUploadStatus(
  assetId: string
): Promise<SketchfabUploadStatus> {
  const { data } = await apiClient.get<SketchfabUploadStatus>(
    `/assets/${assetId}/sketchfab/status`
  );
  return data;
}

export async function importFromSketchfab(
  body: SketchfabImportRequest
): Promise<SketchfabImportResponse> {
  const { data } = await apiClient.post<SketchfabImportResponse>(
    "/assets/sketchfab/import",
    body
  );
  return data;
}

export async function getMySketchfabModels(): Promise<SketchfabMeModelsResponse> {
  const { data } = await apiClient.get<SketchfabMeModelsResponse>(
    "/sketchfab/me/models"
  );
  return data;
}

import { apiClient } from "./client.js";

export interface AssetStepInfo {
  job_id: string;
  provider_key: string;
  file: string;
  generated_at: string | null;
}

export interface AssetListItem {
  asset_id: string;
  created_at: string;
  updated_at: string;
  steps: Record<string, AssetStepInfo>;
  thumbnail_url: string | null;
}

export interface ProcessingEntry {
  operation: string;
  params: Record<string, unknown>;
  source_file: string;
  output_file: string;
  processed_at: string;
}

export interface AssetDetail {
  asset_id: string;
  created_at: string;
  updated_at: string;
  steps: Record<string, Record<string, unknown>>;
  processing?: ProcessingEntry[];
}

export async function listAssets(): Promise<AssetListItem[]> {
  const { data } = await apiClient.get<AssetListItem[]>("/assets");
  return data;
}

export async function getAsset(assetId: string): Promise<AssetDetail> {
  const { data } = await apiClient.get<AssetDetail>(`/assets/${assetId}`);
  return data;
}

export async function createAsset(): Promise<{ asset_id: string }> {
  const { data } = await apiClient.post<{ asset_id: string }>("/assets");
  return data;
}

export interface UploadImageOptions {
  file: File;
  name?: string;
  onProgress?: (percent: number) => void;
}

export interface UploadMeshOptions {
  file: File;
  mtlFile?: File;
  name?: string;
  onProgress?: (percent: number) => void;
}

export interface UploadImageResponse {
  asset_id: string;
  file: string;
}

export async function uploadImage({
  file,
  name,
  onProgress,
}: UploadImageOptions): Promise<UploadImageResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) formData.append("name", name);
  const { data } = await apiClient.post<UploadImageResponse>(
    "/assets/upload/image",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress
        ? (e) => {
            if (e.total && e.total > 0) {
              onProgress(Math.round((e.loaded / e.total) * 100));
            }
          }
        : undefined,
    }
  );
  return data;
}

export interface UploadMeshResponse {
  asset_id: string;
  file: string;
}

export async function uploadMesh({
  file,
  mtlFile,
  name,
  onProgress,
}: UploadMeshOptions): Promise<UploadMeshResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) formData.append("name", name);
  if (mtlFile) formData.append("mtl_file", mtlFile);
  const { data } = await apiClient.post<UploadMeshResponse>(
    "/assets/upload/mesh",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onProgress
        ? (e) => {
            if (e.total && e.total > 0) {
              onProgress(Math.round((e.loaded / e.total) * 100));
            }
          }
        : undefined,
    }
  );
  return data;
}

export function getAssetFileUrl(assetId: string, filename: string): string {
  const baseUrl = apiClient.defaults.baseURL ?? "http://localhost:8000";
  return `${baseUrl}/assets/${assetId}/files/${filename}`;
}

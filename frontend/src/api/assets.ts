import { apiClient } from "./client.js";

export interface AssetStepInfo {
  job_id: string;
  provider_key: string;
  file: string;
  generated_at: string | null;
  name?: string | null;
}

export interface AssetListItem {
  asset_id: string;
  created_at: string;
  updated_at: string;
  steps: Record<string, AssetStepInfo>;
  thumbnail_url: string | null;
  deleted_at?: string | null;
  name?: string | null;
  tags?: string[];
  rating?: number | null;
  favorited?: boolean;
}

export interface ProcessingEntry {
  operation: string;
  params: Record<string, unknown>;
  source_file: string;
  output_file: string;
  processed_at: string;
}

export interface SketchfabUploadInfo {
  uid: string;
  url: string;
  embed_url?: string;
  uploaded_at: string;
  is_private?: boolean;
}

export interface ImageProcessingEntry {
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
  image_processing?: ImageProcessingEntry[];
  sketchfab_upload?: SketchfabUploadInfo | null;
  source?: string | null;
  sketchfab_uid?: string | null;
  sketchfab_url?: string | null;
  sketchfab_author?: string | null;
  downloaded_at?: string | null;
  exports?: ExportEntry[];
  name?: string | null;
  tags?: string[];
  rating?: number | null;
  notes?: string | null;
  favorited?: boolean;
}

export interface AssetMetaUpdate {
  name?: string | null;
  tags?: string[];
  rating?: number | null;
  notes?: string | null;
  favorited?: boolean | null;
}

export interface ListAssetsParams {
  search?: string;
  tags?: string;
  rating?: number;
  has_step?: "image" | "mesh" | "rigging" | "animation";
  favorited?: boolean;
  source?: string;
  sort?: "created_desc" | "created_asc" | "name" | "rating";
}

export interface ExportEntry {
  format: string;
  source_file: string;
  output_file: string;
  exported_at: string;
  file_size_bytes: number;
}

export interface ExportRequest {
  source_file: string;
  format: "stl" | "obj" | "ply" | "gltf";
}

export interface ExportResponse {
  output_file: string;
  format: string;
  file_size_bytes: number;
  download_url: string;
}

export interface ExportListItem {
  filename: string;
  format: string;
  source_file: string;
  exported_at: string;
  file_size_bytes: number;
  download_url: string;
}

export async function listAssets(
  params?: ListAssetsParams & { includeDeleted?: boolean }
): Promise<AssetListItem[]> {
  const p = params ?? {};
  const { includeDeleted, ...rest } = p;
  const queryParams = {
    ...rest,
    ...(includeDeleted ? { include_deleted: "true" } : {}),
  };
  const { data } = await apiClient.get<AssetListItem[]>("/assets", {
    params: queryParams,
  });
  return data;
}

export async function getAssetTags(): Promise<{ tags: string[] }> {
  const { data } = await apiClient.get<{ tags: string[] }>("/assets/tags");
  return data;
}

export async function patchAssetMeta(
  assetId: string,
  meta: AssetMetaUpdate
): Promise<{ message: string }> {
  const { data } = await apiClient.patch<{ message: string }>(
    `/assets/${assetId}/meta`,
    meta
  );
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

export async function exportMesh(
  assetId: string,
  req: ExportRequest
): Promise<ExportResponse> {
  const { data } = await apiClient.post<ExportResponse>(
    `/assets/${assetId}/export`,
    req
  );
  return data;
}

export async function getAssetExports(
  assetId: string
): Promise<{ exports: ExportListItem[] }> {
  const { data } = await apiClient.get<{ exports: ExportListItem[] }>(
    `/assets/${assetId}/exports`
  );
  return data;
}

export async function deleteAsset(
  assetId: string,
  permanent = false
): Promise<void> {
  await apiClient.delete(`/assets/${assetId}`, {
    params: permanent ? { permanent: "true" } : undefined,
  });
}

export async function deleteAssetBatch(
  assetIds: string[],
  permanent = false
): Promise<{ deleted_count: number }> {
  const { data } = await apiClient.delete<{ deleted_count: number }>(
    "/assets/batch",
    { data: { asset_ids: assetIds, permanent } }
  );
  return data;
}

export async function restoreAsset(assetId: string): Promise<void> {
  await apiClient.post(`/assets/${assetId}/restore`);
}

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
  exports?: ExportEntry[];
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

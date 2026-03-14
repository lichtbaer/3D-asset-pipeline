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

export interface SketchfabUploadInfo {
  uid: string;
  url: string;
  embed_url?: string;
  uploaded_at: string;
  is_private?: boolean;
}

export interface AssetDetail {
  asset_id: string;
  created_at: string;
  updated_at: string;
  steps: Record<string, Record<string, unknown>>;
  processing?: ProcessingEntry[];
  sketchfab_upload?: SketchfabUploadInfo | null;
  source?: string | null;
  sketchfab_uid?: string | null;
  sketchfab_url?: string | null;
  sketchfab_author?: string | null;
  downloaded_at?: string | null;
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

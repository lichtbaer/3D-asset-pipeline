import { apiClient } from "./client.js";

export interface StorageBreakdownItem {
  count: number;
  size_bytes: number;
}

export interface StorageStats {
  total_size_bytes: number;
  total_size_human: string;
  asset_count: number;
  deleted_count: number;
  deleted_size_bytes: number;
  breakdown: {
    images: StorageBreakdownItem;
    meshes: StorageBreakdownItem;
    rigs: StorageBreakdownItem;
    animations: StorageBreakdownItem;
    exports: StorageBreakdownItem;
  };
}

export async function getStorageStats(): Promise<StorageStats> {
  const { data } = await apiClient.get<StorageStats>("/storage/stats");
  return data;
}

export interface PurgeDeletedResponse {
  deleted_count: number;
  freed_bytes: number;
}

export async function purgeDeleted(): Promise<PurgeDeletedResponse> {
  const { data } = await apiClient.post<PurgeDeletedResponse>(
    "/storage/purge-deleted"
  );
  return data;
}

import { apiClient } from "./client.js";

export interface ImageProcessingResponse {
  output_file: string;
  width: number;
  height: number;
  file_size_bytes: number;
}

export async function getImageSources(
  assetId: string
): Promise<{ sources: string[] }> {
  const { data } = await apiClient.get<{ sources: string[] }>(
    `/assets/${assetId}/image/sources`
  );
  return data;
}

export async function cropImage(
  assetId: string,
  req: {
    source_file: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }
): Promise<ImageProcessingResponse> {
  const { data } = await apiClient.post<ImageProcessingResponse>(
    `/assets/${assetId}/image/crop`,
    req
  );
  return data;
}

export async function resizeImage(
  assetId: string,
  req: {
    source_file: string;
    width: number;
    height: number;
    maintain_aspect?: boolean;
  }
): Promise<ImageProcessingResponse> {
  const { data } = await apiClient.post<ImageProcessingResponse>(
    `/assets/${assetId}/image/resize`,
    req
  );
  return data;
}

export async function centerImage(
  assetId: string,
  req: {
    source_file: string;
    padding?: number;
  }
): Promise<ImageProcessingResponse> {
  const { data } = await apiClient.post<ImageProcessingResponse>(
    `/assets/${assetId}/image/center`,
    req
  );
  return data;
}

export async function padSquareImage(
  assetId: string,
  req: {
    source_file: string;
    background?: string;
  }
): Promise<ImageProcessingResponse> {
  const { data } = await apiClient.post<ImageProcessingResponse>(
    `/assets/${assetId}/image/pad-square`,
    req
  );
  return data;
}

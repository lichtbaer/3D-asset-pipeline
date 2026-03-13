import { apiClient } from "./client.js";

export interface MeshAnalysis {
  vertex_count: number;
  face_count: number;
  is_watertight: boolean;
  is_manifold: boolean;
  has_duplicate_vertices: boolean;
  bounding_box: {
    min_x: number;
    max_x: number;
    min_y: number;
    max_y: number;
    min_z: number;
    max_z: number;
  };
  file_size_bytes: number;
}

export type RepairOperation =
  | "remove_duplicates"
  | "fix_normals"
  | "fill_holes"
  | "remove_degenerate";

export interface SimplifyRequest {
  source_file: string;
  target_faces: number;
}

export interface RepairRequest {
  source_file: string;
  operations: RepairOperation[];
}

export interface ProcessingResult {
  output_file: string;
  processing: {
    operation: string;
    params: Record<string, unknown>;
    source_file: string;
    output_file: string;
    processed_at: string;
  };
}

export async function analyzeMesh(
  assetId: string,
  sourceFile: string = "mesh.glb"
): Promise<MeshAnalysis> {
  const { data } = await apiClient.get<MeshAnalysis>(
    `/assets/${assetId}/process/analyze`,
    { params: { source_file: sourceFile } }
  );
  return data;
}

export async function simplifyMesh(
  assetId: string,
  req: SimplifyRequest
): Promise<ProcessingResult> {
  const { data } = await apiClient.post<ProcessingResult>(
    `/assets/${assetId}/process/simplify`,
    req
  );
  return data;
}

export async function repairMesh(
  assetId: string,
  req: RepairRequest
): Promise<ProcessingResult> {
  const { data } = await apiClient.post<ProcessingResult>(
    `/assets/${assetId}/process/repair`,
    req
  );
  return data;
}

export async function getMeshSources(
  assetId: string
): Promise<{ sources: string[] }> {
  const { data } = await apiClient.get<{ sources: string[] }>(
    `/assets/${assetId}/process/sources`
  );
  return data;
}

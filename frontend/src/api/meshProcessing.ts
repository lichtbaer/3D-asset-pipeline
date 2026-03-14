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

export interface ClipFloorRequest {
  source_file: string;
  y_threshold?: number | null;
}

export interface ClipFloorResult {
  output_file: string;
  y_threshold_used: number;
  vertices_removed: number;
  faces_removed: number;
}

export interface RemoveComponentsRequest {
  source_file: string;
  min_component_ratio?: number;
}

export interface RemoveComponentsResult {
  output_file: string;
  components_found: number;
  components_removed: number;
  triangles_removed: number;
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

export async function clipFloor(
  assetId: string,
  req: ClipFloorRequest
): Promise<ClipFloorResult> {
  const { data } = await apiClient.post<ClipFloorResult>(
    `/assets/${assetId}/process/clip-floor`,
    req
  );
  return data;
}

export async function removeComponents(
  assetId: string,
  req: RemoveComponentsRequest
): Promise<RemoveComponentsResult> {
  const { data } = await apiClient.post<RemoveComponentsResult>(
    `/assets/${assetId}/process/remove-components`,
    req
  );
  return data;
}

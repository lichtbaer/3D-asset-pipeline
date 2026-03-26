import { apiClient } from "./client.js";
import type { ProviderParamValue } from "./generation.js";

export interface PresetStep {
  step: string;
  provider: string | null;
  params: Record<string, ProviderParamValue>;
}

export interface Preset {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  steps: PresetStep[];
}

export interface PresetCreate {
  name: string;
  description: string;
  steps: PresetStep[];
}

export interface PresetApplyRequest {
  asset_id: string;
  start_from_step?: number;
  dry_run?: boolean;
}

export interface ExecutionPlanItem {
  step_index: number;
  step: string;
  provider: string | null;
  params: Record<string, ProviderParamValue>;
  status: "skipped" | "applicable";
  reason: string | null;
}

export interface PresetApplyResponse {
  preset_id: string;
  asset_id: string;
  steps_total: number;
  steps_applicable: number;
  steps_skipped: number;
  execution_plan: ExecutionPlanItem[];
}

export interface PresetSuggestions {
  suggested_name: string;
  steps: PresetStep[];
}

export async function listPresets(): Promise<Preset[]> {
  const { data } = await apiClient.get<Preset[]>("/presets");
  return data;
}

export async function getPreset(presetId: string): Promise<Preset> {
  const { data } = await apiClient.get<Preset>(`/presets/${presetId}`);
  return data;
}

export async function createPreset(
  preset: PresetCreate
): Promise<Preset> {
  const { data } = await apiClient.post<Preset>("/presets", preset);
  return data;
}

export async function updatePreset(
  presetId: string,
  updates: Partial<PresetCreate>
): Promise<Preset> {
  const { data } = await apiClient.put<Preset>(`/presets/${presetId}`, updates);
  return data;
}

export async function deletePreset(presetId: string): Promise<void> {
  await apiClient.delete(`/presets/${presetId}`);
}

export async function applyPreset(
  presetId: string,
  req: PresetApplyRequest
): Promise<PresetApplyResponse> {
  const { data } = await apiClient.post<PresetApplyResponse>(
    `/presets/${presetId}/apply`,
    req
  );
  return data;
}

export async function getPresetSuggestions(
  assetId: string
): Promise<PresetSuggestions> {
  const { data } = await apiClient.get<PresetSuggestions>(
    `/assets/${assetId}/preset-suggestions`
  );
  return data;
}

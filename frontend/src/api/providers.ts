/**
 * API-Client für Provider-Gesundheitsstatus.
 * Endpoint: GET /providers/health
 */

import { apiClient } from "./client.js";

export type ProviderStatus = "healthy" | "degraded" | "unavailable";

export interface ProviderHealthInfo {
  key: string;
  display_name: string;
  provider_type: "image" | "mesh" | "bgremoval" | "rigging" | "animation";
  status: ProviderStatus;
  reason: string | null;
}

export interface ProvidersHealthResponse {
  providers: ProviderHealthInfo[];
  cached: boolean;
  checked_at: number;
}

export async function getProvidersHealth(): Promise<ProvidersHealthResponse> {
  const { data } = await apiClient.get<ProvidersHealthResponse>(
    "/providers/health"
  );
  return data;
}

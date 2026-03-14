import { apiClient } from "./client.js";

export type PromptIntendedUse = "rigging" | "mesh_only" | "3d_print";

export interface PromptOptimizeRequest {
  description: string;
  style?: string | null;
  intended_use?: PromptIntendedUse;
  existing_prompt?: string | null;
}

export interface PromptSuggestion {
  optimized_prompt: string;
  negative_prompt: string;
  reasoning: string;
  variants: string[];
}

export interface AgentError {
  agent: string;
  error_type: string;
  message: string;
  fallback_available: boolean;
}

export async function optimizePrompt(
  req: PromptOptimizeRequest
): Promise<PromptSuggestion> {
  const { data } = await apiClient.post<PromptSuggestion>(
    "/agents/prompt/optimize",
    req
  );
  return data;
}

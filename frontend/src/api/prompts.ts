import { apiClient } from "./client.js";

export interface PromptHistoryItem {
  prompt: string;
  last_used_at: string;
  use_count: number;
}

export async function getPromptHistory(limit = 30): Promise<PromptHistoryItem[]> {
  const { data } = await apiClient.get<{ items: PromptHistoryItem[] }>(
    "/generate/prompts/history",
    { params: { limit } }
  );
  return data.items;
}

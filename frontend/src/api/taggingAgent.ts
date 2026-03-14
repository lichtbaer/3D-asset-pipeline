import { apiClient } from "./client.js";

export interface TagSuggestRequest {
  asset_id: string;
  prompt?: string | null;
  original_filename?: string | null;
  pipeline_steps?: string[];
  include_image_analysis?: boolean;
}

export interface TagSuggestion {
  tags: string[];
  confidence: number;
}

export async function suggestTags(
  req: TagSuggestRequest
): Promise<TagSuggestion> {
  const { data } = await apiClient.post<TagSuggestion>(
    "/agents/tags/suggest",
    req
  );
  return data;
}

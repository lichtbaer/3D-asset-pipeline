import { apiClient } from "./client.js";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatActionParams {
  prompt?: string;
  tags?: string[];
  tab?: string;
  asset_id?: string;
  [key: string]: string | string[] | number | boolean | null | undefined;
}

export interface ChatAction {
  type: "optimize_prompt" | "suggest_tags" | "assess_quality" | "open_tab";
  params: ChatActionParams;
}

export interface ChatResponse {
  message: string;
  suggestions: string[];
  prompt_suggestion: string | null;
  action: ChatAction | null;
}

export interface ChatRequest {
  message: string;
  history?: ChatMessage[];
  asset_id?: string | null;
  max_history?: number;
}

export async function sendChatMessage(
  req: ChatRequest
): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>("/agents/chat", {
    message: req.message,
    history: req.history ?? [],
    asset_id: req.asset_id ?? null,
    max_history: req.max_history ?? 10,
  });
  return data;
}

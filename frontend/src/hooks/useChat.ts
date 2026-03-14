import { useCallback, useEffect, useState } from "react";
import { sendChatMessage } from "../api/chat.js";
import type { ChatMessage } from "../api/chat.js";

const STORAGE_KEY = "purzel-chat-history";

function loadHistory(): ChatMessage[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (m): m is ChatMessage =>
        m &&
        typeof m === "object" &&
        (m.role === "user" || m.role === "assistant") &&
        typeof m.content === "string" &&
        typeof m.timestamp === "string"
    );
  } catch {
    return [];
  }
}

function saveHistory(messages: ChatMessage[]): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch {
    // ignore
  }
}

export interface UseChatOptions {
  assetId?: string | null;
}

export interface LastResponseMeta {
  suggestions: string[];
  promptSuggestion: string | null;
}

export interface UseChatResult {
  messages: ChatMessage[];
  lastResponseMeta: LastResponseMeta | null;
  sendMessage: (content: string) => Promise<void>;
  clearHistory: () => void;
  isLoading: boolean;
  error: string | null;
}

export function useChat({ assetId }: UseChatOptions = {}): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>(loadHistory);
  const [lastResponseMeta, setLastResponseMeta] =
    useState<LastResponseMeta | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    saveHistory(messages);
  }, [messages]);

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed) return;

      const userMsg: ChatMessage = {
        role: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      try {
        const history = [...messages, userMsg].slice(-10);
        const res = await sendChatMessage({
          message: trimmed,
          history,
          asset_id: assetId ?? null,
          max_history: 10,
        });

        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: res.message,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setLastResponseMeta({
          suggestions: res.suggestions ?? [],
          promptSuggestion: res.prompt_suggestion ?? null,
        });
      } catch (e) {
        let errMsg: string;
        if (e && typeof e === "object" && "response" in e) {
          const res = (e as { response?: { data?: { detail?: unknown } } })
            .response?.data?.detail;
          errMsg =
            typeof res === "string"
              ? res
              : res && typeof res === "object" && "message" in res
                ? String((res as { message: unknown }).message)
                : "Fehler beim Senden";
        } else {
          errMsg = e instanceof Error ? e.message : "Fehler beim Senden";
        }
        setError(errMsg);
        const fallbackMsg: ChatMessage = {
          role: "assistant",
          content: `Fehler: ${errMsg}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, fallbackMsg]);
        setLastResponseMeta(null);
      } finally {
        setIsLoading(false);
      }
    },
    [assetId, messages]
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    setLastResponseMeta(null);
    setError(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  return {
    messages,
    lastResponseMeta,
    sendMessage,
    clearHistory,
    isLoading,
    error,
  };
}

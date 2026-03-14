import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChat } from "../../hooks/useChat.js";

vi.mock("../../api/chat.js", () => ({
  sendChatMessage: vi.fn(),
}));

const STORAGE_KEY = "purzel-chat-history";

describe("useChat", () => {
  beforeEach(async () => {
    sessionStorage.clear();
    vi.clearAllMocks();
    const { sendChatMessage } = await import("../../api/chat.js");
    vi.mocked(sendChatMessage).mockResolvedValue({
      message: "Antwort",
      suggestions: [],
      prompt_suggestion: null,
      action: null,
    });
  });

  it("lädt leere History aus sessionStorage", () => {
    const { result } = renderHook(() => useChat());
    expect(result.current.messages).toEqual([]);
  });

  it("verwaltet History korrekt in sessionStorage", async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      result.current.sendMessage("Hallo");
    });

    const stored = sessionStorage.getItem(STORAGE_KEY);
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(Array.isArray(parsed)).toBe(true);
    expect(parsed.length).toBeGreaterThanOrEqual(1);
  });

  it("clearHistory leert Messages und sessionStorage", async () => {
    const { result } = renderHook(() => useChat());
    await act(async () => {
      result.current.sendMessage("Test");
    });
    expect(result.current.messages.length).toBeGreaterThan(0);

    act(() => {
      result.current.clearHistory();
    });
    expect(result.current.messages).toEqual([]);
    const stored = sessionStorage.getItem(STORAGE_KEY);
    expect(result.current.messages).toEqual([]);
  });

  it("ignoriert leere Nachrichten", async () => {
    const { result } = renderHook(() => useChat());
    const lenBefore = result.current.messages.length;

    await act(async () => {
      result.current.sendMessage("   ");
    });

    expect(result.current.messages.length).toBe(lenBefore);
  });
});

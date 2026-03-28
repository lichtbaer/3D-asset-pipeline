import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useJobStream } from "../../hooks/useJobStream.js";

// Mock EventSource
type MessageHandler = (e: { data: string }) => void;
type EventHandler = (e?: { data?: string }) => void;

class MockEventSource {
  url: string;
  onmessage: MessageHandler | null = null;
  onerror: EventHandler | null = null;
  readyState = 0;
  static CLOSED = 2;
  private _listeners: Map<string, EventHandler[]> = new Map();

  constructor(url: string) {
    this.url = url;
  }

  addEventListener(type: string, handler: EventHandler) {
    if (!this._listeners.has(type)) {
      this._listeners.set(type, []);
    }
    this._listeners.get(type)!.push(handler);
  }

  dispatchMessage(data: string) {
    this.onmessage?.({ data });
  }

  dispatchEvent(type: string, data?: string) {
    const handlers = this._listeners.get(type) ?? [];
    handlers.forEach((h) => h(data ? { data } : {}));
  }

  close() {
    this.readyState = MockEventSource.CLOSED;
  }
}

let mockEventSources: MockEventSource[] = [];

vi.stubGlobal("EventSource", class {
  constructor(url: string) {
    const instance = new MockEventSource(url);
    mockEventSources.push(instance);
    return instance;
  }
  static CLOSED = MockEventSource.CLOSED;
});

// Mock API client import in hook
vi.mock("../../api/client.js", () => ({
  API_BASE: "http://localhost:8000",
  apiClient: { get: vi.fn() },
}));

describe("useJobStream", () => {
  beforeEach(() => {
    mockEventSources = [];
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("gibt initialen Zustand zurück", () => {
    const { result } = renderHook(() => useJobStream("test-job-id"));

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("startet keinen Stream wenn jobId null", () => {
    renderHook(() => useJobStream(null));
    expect(mockEventSources).toHaveLength(0);
  });

  it("startet keinen Stream wenn enabled=false", () => {
    renderHook(() => useJobStream("test-job", { enabled: false }));
    expect(mockEventSources).toHaveLength(0);
  });

  it("erstellt EventSource wenn jobId gesetzt", () => {
    renderHook(() => useJobStream("test-job-id"));
    expect(mockEventSources).toHaveLength(1);
    expect(mockEventSources[0].url).toContain("test-job-id");
  });

  it("aktualisiert data bei SSE-Nachricht", () => {
    const { result } = renderHook(() => useJobStream("test-job-id"));

    const jobData = {
      job_id: "test-job-id",
      job_type: "image",
      status: "processing",
      result_url: null,
      glb_file_path: null,
      asset_id: null,
      error_type: null,
      error_detail: null,
      updated_at: "2026-03-28T00:00:00Z",
    };

    act(() => {
      mockEventSources[0].dispatchMessage(JSON.stringify(jobData));
    });

    expect(result.current.data?.status).toBe("processing");
    expect(result.current.data?.job_id).toBe("test-job-id");
  });

  it("schließt Stream wenn Job done ist", () => {
    const { result } = renderHook(() => useJobStream("test-job-id"));

    const doneData = {
      job_id: "test-job-id",
      job_type: "image",
      status: "done",
      result_url: "http://example.com/result.png",
      glb_file_path: null,
      asset_id: "asset-123",
      error_type: null,
      error_detail: null,
      updated_at: "2026-03-28T00:00:01Z",
    };

    act(() => {
      mockEventSources[0].dispatchMessage(JSON.stringify(doneData));
    });

    expect(result.current.data?.status).toBe("done");
    expect(mockEventSources[0].readyState).toBe(MockEventSource.CLOSED);
  });

  it("ignoriert ungültige JSON-Daten", () => {
    const { result } = renderHook(() => useJobStream("test-job-id"));

    act(() => {
      mockEventSources[0].dispatchMessage("kein gültiges JSON {{{");
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });
});

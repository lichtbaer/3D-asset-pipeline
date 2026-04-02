import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AutoPipelinePanel } from "../../components/pipeline/AutoPipelinePanel.js";
import { PipelineStoreProvider } from "../../store/PipelineStore.js";

// Mock API
const mockStartPipelineRun = vi.fn();
vi.mock("../../api/pipeline.js", () => ({
  startPipelineRun: (...args: unknown[]) => mockStartPipelineRun(...args),
  getPipelineStreamUrl: (id: string) => `http://localhost:8000/api/v1/generate/pipeline/${id}/stream`,
}));

// Mock EventSource
class MockEventSource {
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0;
  static CLOSED = 2;

  constructor(url: string) {
    this.url = url;
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  addEventListener(_type: string, _handler: unknown) {}
  close() { this.readyState = MockEventSource.CLOSED; }
}

vi.stubGlobal("EventSource", MockEventSource);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <PipelineStoreProvider>{children}</PipelineStoreProvider>
      </QueryClientProvider>
    );
  };
}

describe("AutoPipelinePanel", () => {
  beforeEach(() => {
    mockStartPipelineRun.mockReset();
  });

  it("rendert Formular mit Pflichtfeldern", () => {
    render(<AutoPipelinePanel />, { wrapper: createWrapper() });

    expect(screen.getByLabelText(/Beschreibung/)).toBeDefined();
    expect(screen.getByRole("button", { name: /Pipeline starten/ })).toBeDefined();
  });

  it("deaktiviert Submit-Button bei leerem Prompt", () => {
    render(<AutoPipelinePanel />, { wrapper: createWrapper() });

    const submitBtn = screen.getByRole("button", { name: /Pipeline starten/ });
    expect(submitBtn).toBeDisabled();
  });

  it("aktiviert Submit-Button bei Prompt-Eingabe", () => {
    render(<AutoPipelinePanel />, { wrapper: createWrapper() });

    const textarea = screen.getByLabelText(/Beschreibung/);
    fireEvent.change(textarea, { target: { value: "Ein Roboter" } });

    const submitBtn = screen.getByRole("button", { name: /Pipeline starten/ });
    expect(submitBtn).not.toBeDisabled();
  });

  it("zeigt Standard-Optionen", () => {
    render(<AutoPipelinePanel />, { wrapper: createWrapper() });

    expect(screen.getByLabelText(/Background-Removal/)).toBeDefined();
    expect(screen.getByLabelText(/Rigging/)).toBeDefined();
    expect(screen.getByLabelText(/Animation/)).toBeDefined();
  });

  it("Background-Removal ist standardmäßig aktiviert", () => {
    render(<AutoPipelinePanel />, { wrapper: createWrapper() });

    const bgCheckbox = screen.getByLabelText(/Background-Removal/);
    expect((bgCheckbox as HTMLInputElement).checked).toBe(true);
  });

  it("startet Pipeline bei Submit", async () => {
    mockStartPipelineRun.mockResolvedValue({
      pipeline_run_id: "test-id",
      status: "running",
      asset_id: null,
      steps: [],
      created_at: "2026-03-28T00:00:00Z",
    });

    render(<AutoPipelinePanel />, { wrapper: createWrapper() });

    const textarea = screen.getByLabelText(/Beschreibung/);
    fireEvent.change(textarea, { target: { value: "Ein Drache" } });

    const submitBtn = screen.getByRole("button", { name: /Pipeline starten/ });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockStartPipelineRun).toHaveBeenCalledWith(
        expect.objectContaining({ prompt: "Ein Drache" })
      );
    });
  });

  it("zeigt Fehler bei fehlgeschlagenem API-Aufruf", async () => {
    mockStartPipelineRun.mockRejectedValue(new Error("Server nicht erreichbar"));

    render(<AutoPipelinePanel />, { wrapper: createWrapper() });

    const textarea = screen.getByLabelText(/Beschreibung/);
    fireEvent.change(textarea, { target: { value: "Test" } });
    fireEvent.click(screen.getByRole("button", { name: /Pipeline starten/ }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeDefined();
    });
  });

  it("nimmt initialPrompt als Standard-Wert", () => {
    render(<AutoPipelinePanel initialPrompt="Vorgefertigter Prompt" />, {
      wrapper: createWrapper(),
    });

    const textarea = screen.getByLabelText(/Beschreibung/) as HTMLTextAreaElement;
    expect(textarea.value).toBe("Vorgefertigter Prompt");
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  startPipelineRun,
  getPipelineRunStatus,
  getPipelineStreamUrl,
} from "../../api/pipeline.js";
import { apiClient } from "../../api/client.js";

vi.mock("../../api/client.js", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
  API_BASE: "http://localhost:8000",
}));

const mockRunStatus = {
  pipeline_run_id: "test-run-id",
  status: "running" as const,
  asset_id: null,
  steps: [
    { step: "image", job_id: null, status: "pending" as const, result_url: null, error: null },
    { step: "bgremoval", job_id: null, status: "pending" as const, result_url: null, error: null },
    { step: "mesh", job_id: null, status: "pending" as const, result_url: null, error: null },
    { step: "rigging", job_id: null, status: "skipped" as const, result_url: null, error: null },
    { step: "animation", job_id: null, status: "skipped" as const, result_url: null, error: null },
  ],
  created_at: "2026-03-28T00:00:00Z",
  updated_at: null,
  error: null,
};

describe("pipeline API", () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset();
    vi.mocked(apiClient.get).mockReset();
  });

  describe("startPipelineRun", () => {
    it("schickt POST /generate/pipeline/run mit korrekten Parametern", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockRunStatus });

      const request = {
        prompt: "Ein Roboter",
        enable_bgremoval: true,
        enable_rigging: false,
        enable_animation: false,
      };

      const result = await startPipelineRun(request);

      expect(apiClient.post).toHaveBeenCalledWith(
        "/generate/pipeline/run",
        request
      );
      expect(result).toEqual(mockRunStatus);
    });

    it("gibt die Server-Antwort zurück", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockRunStatus });
      const result = await startPipelineRun({ prompt: "Test" });
      expect(result.pipeline_run_id).toBe("test-run-id");
      expect(result.status).toBe("running");
      expect(result.steps).toHaveLength(5);
    });
  });

  describe("getPipelineRunStatus", () => {
    it("schickt GET /generate/pipeline/{id}", async () => {
      const doneStatus = { ...mockRunStatus, status: "done" as const };
      vi.mocked(apiClient.get).mockResolvedValue({ data: doneStatus });

      const result = await getPipelineRunStatus("test-run-id");

      expect(apiClient.get).toHaveBeenCalledWith(
        "/generate/pipeline/test-run-id"
      );
      expect(result.status).toBe("done");
    });
  });

  describe("getPipelineStreamUrl", () => {
    it("gibt korrekte SSE-URL ohne API-Key zurück", () => {
      const url = getPipelineStreamUrl("test-run-id");
      expect(url).toBe(
        "http://localhost:8000/api/v1/generate/pipeline/test-run-id/stream"
      );
    });
  });
});

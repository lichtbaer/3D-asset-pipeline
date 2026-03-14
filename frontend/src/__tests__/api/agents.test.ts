import { describe, it, expect, vi, beforeEach } from "vitest";
import { assessQuality, recommendWorkflow } from "../../api/agents.js";
import { apiClient } from "../../api/client.js";

vi.mock("../../api/client.js", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

describe("agents API", () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset();
  });

  it("assessQuality ruft POST /agents/quality/assess auf", async () => {
    const mockResponse = {
      score: 8,
      issues: [],
      rigging_suitable: true,
      recommended_actions: [],
    };
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

    const result = await assessQuality({
      asset_id: "test-asset",
      include_mesh_analysis: true,
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/agents/quality/assess",
      expect.objectContaining({ asset_id: "test-asset" })
    );
    expect(result).toEqual(mockResponse);
  });

  it("recommendWorkflow ruft POST /agents/workflow/recommend auf", async () => {
    const mockResponse = {
      next_step: "rig" as const,
      reason: "Mesh ist bereit",
      alternative_steps: [],
      warnings: [],
    };
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

    const result = await recommendWorkflow({
      asset_id: "test-asset",
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/agents/workflow/recommend",
      expect.objectContaining({ asset_id: "test-asset" })
    );
    expect(result).toEqual(mockResponse);
  });
});

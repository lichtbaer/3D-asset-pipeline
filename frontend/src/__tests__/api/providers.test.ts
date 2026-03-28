import { describe, it, expect, vi, beforeEach } from "vitest";
import { getProvidersHealth } from "../../api/providers.js";
import { apiClient } from "../../api/client.js";

vi.mock("../../api/client.js", () => ({
  apiClient: {
    get: vi.fn(),
  },
  API_BASE: "http://localhost:8000",
}));

const mockHealthResponse = {
  providers: [
    {
      key: "picsart-default",
      display_name: "PicsArt Standard",
      provider_type: "image" as const,
      status: "healthy" as const,
      reason: null,
    },
    {
      key: "hunyuan3d-2",
      display_name: "Hunyuan3D-2 (HF Space)",
      provider_type: "mesh" as const,
      status: "unavailable" as const,
      reason: "HF_TOKEN nicht gesetzt",
    },
    {
      key: "rembg-local",
      display_name: "rembg (lokal)",
      provider_type: "bgremoval" as const,
      status: "healthy" as const,
      reason: null,
    },
  ],
  cached: false,
  checked_at: 1711584000.0,
};

describe("providers API", () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
  });

  it("ruft GET /providers/health auf", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockHealthResponse });

    const result = await getProvidersHealth();

    expect(apiClient.get).toHaveBeenCalledWith("/providers/health");
    expect(result).toEqual(mockHealthResponse);
  });

  it("gibt providers mit Status zurück", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockHealthResponse });

    const result = await getProvidersHealth();

    expect(result.providers).toHaveLength(3);
    expect(result.providers[0].status).toBe("healthy");
    expect(result.providers[1].status).toBe("unavailable");
    expect(result.providers[1].reason).toBe("HF_TOKEN nicht gesetzt");
  });

  it("gibt cached-Flag zurück", async () => {
    const cachedResponse = { ...mockHealthResponse, cached: true };
    vi.mocked(apiClient.get).mockResolvedValue({ data: cachedResponse });

    const result = await getProvidersHealth();
    expect(result.cached).toBe(true);
  });
});

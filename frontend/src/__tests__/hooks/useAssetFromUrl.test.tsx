import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAssetFromUrl } from "../../hooks/useAssetFromUrl.js";
import { useSearchParams } from "react-router-dom";

vi.mock("react-router-dom", () => ({
  useSearchParams: vi.fn(),
}));

const mockGetAsset = vi.fn();
vi.mock("../../api/assets.js", () => ({
  getAsset: (...args: unknown[]) => mockGetAsset(...args),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useAssetFromUrl", () => {
  beforeEach(() => {
    vi.mocked(useSearchParams).mockReturnValue([
      new URLSearchParams(),
      vi.fn(),
    ] as ReturnType<typeof useSearchParams>);
    mockGetAsset.mockReset();
  });

  it("gibt null zurück wenn kein assetId in URL", () => {
    vi.mocked(useSearchParams).mockReturnValue([
      new URLSearchParams(),
      vi.fn(),
    ] as ReturnType<typeof useSearchParams>);

    const { result } = renderHook(() => useAssetFromUrl(), {
      wrapper: createWrapper(),
    });

    expect(result.current.assetId).toBeNull();
    expect(result.current.asset).toBeNull();
  });

  it("lädt Asset aus URL-Parameter", async () => {
    const mockAsset = { asset_id: "test-123", steps: {} };
    mockGetAsset.mockResolvedValue(mockAsset);

    vi.mocked(useSearchParams).mockReturnValue([
      new URLSearchParams({ assetId: "test-123" }),
      vi.fn(),
    ] as ReturnType<typeof useSearchParams>);

    const { result } = renderHook(() => useAssetFromUrl(), {
      wrapper: createWrapper(),
    });

    expect(result.current.assetId).toBe("test-123");

    await waitFor(() => {
      expect(result.current.asset).toEqual(mockAsset);
    });
  });
});

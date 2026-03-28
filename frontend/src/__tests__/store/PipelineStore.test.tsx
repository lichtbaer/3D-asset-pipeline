import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { PipelineStoreProvider, usePipelineStore } from "../../store/PipelineStore.js";

function wrapper({ children }: { children: React.ReactNode }) {
  return <PipelineStoreProvider>{children}</PipelineStoreProvider>;
}

describe("PipelineStore", () => {
  it("liefert initialen Zustand", () => {
    const { result } = renderHook(() => usePipelineStore(), { wrapper });

    expect(result.current.activeAssetId).toBeNull();
    expect(result.current.pendingRiggingGlbUrl).toBeNull();
    expect(result.current.pendingAnimationGlbUrl).toBeNull();
    expect(result.current.pendingPromptFromChat).toBeNull();
  });

  it("setzt activeAssetId", () => {
    const { result } = renderHook(() => usePipelineStore(), { wrapper });

    act(() => {
      result.current.setActiveAssetId("test-asset-123");
    });

    expect(result.current.activeAssetId).toBe("test-asset-123");
  });

  it("setzt activeAssetId auf null zurück", () => {
    const { result } = renderHook(() => usePipelineStore(), { wrapper });

    act(() => {
      result.current.setActiveAssetId("test-asset-123");
    });
    act(() => {
      result.current.setActiveAssetId(null);
    });

    expect(result.current.activeAssetId).toBeNull();
  });

  it("setzt pendingRiggingGlbUrl", () => {
    const { result } = renderHook(() => usePipelineStore(), { wrapper });

    act(() => {
      result.current.setPendingRiggingGlbUrl("/static/meshes/test.glb");
    });

    expect(result.current.pendingRiggingGlbUrl).toBe("/static/meshes/test.glb");
  });

  it("setzt pendingAnimationGlbUrl", () => {
    const { result } = renderHook(() => usePipelineStore(), { wrapper });

    act(() => {
      result.current.setPendingAnimationGlbUrl("/static/animations/test_animated.glb");
    });

    expect(result.current.pendingAnimationGlbUrl).toBe("/static/animations/test_animated.glb");
  });

  it("setzt pendingPromptFromChat", () => {
    const { result } = renderHook(() => usePipelineStore(), { wrapper });

    act(() => {
      result.current.setPendingPromptFromChat("Ein roter Drachen");
    });

    expect(result.current.pendingPromptFromChat).toBe("Ein roter Drachen");
  });

  it("wirft Fehler außerhalb des Providers", () => {
    expect(() => {
      renderHook(() => usePipelineStore());
    }).toThrow();
  });
});

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

interface PipelineStoreContextValue {
  activeAssetId: string | null;
  setActiveAssetId: (id: string | null) => void;
  pendingRiggingGlbUrl: string | null;
  setPendingRiggingGlbUrl: (url: string | null) => void;
  pendingAnimationGlbUrl: string | null;
  setPendingAnimationGlbUrl: (url: string | null) => void;
}

const PipelineStoreContext = createContext<PipelineStoreContextValue | null>(
  null
);

export function PipelineStoreProvider({ children }: { children: ReactNode }) {
  const [activeAssetId, setActiveAssetIdState] = useState<string | null>(null);
  const [pendingRiggingGlbUrl, setPendingRiggingGlbUrlState] = useState<
    string | null
  >(null);
  const [pendingAnimationGlbUrl, setPendingAnimationGlbUrlState] = useState<
    string | null
  >(null);

  const setActiveAssetId = useCallback((id: string | null) => {
    setActiveAssetIdState(id);
  }, []);
  const setPendingRiggingGlbUrl = useCallback((url: string | null) => {
    setPendingRiggingGlbUrlState(url);
  }, []);
  const setPendingAnimationGlbUrl = useCallback((url: string | null) => {
    setPendingAnimationGlbUrlState(url);
  }, []);

  return (
    <PipelineStoreContext.Provider
      value={{
        activeAssetId,
        setActiveAssetId,
        pendingRiggingGlbUrl,
        setPendingRiggingGlbUrl,
        pendingAnimationGlbUrl,
        setPendingAnimationGlbUrl,
      }}
    >
      {children}
    </PipelineStoreContext.Provider>
  );
}

export function usePipelineStore(): PipelineStoreContextValue {
  const ctx = useContext(PipelineStoreContext);
  if (!ctx) {
    throw new Error("usePipelineStore must be used within PipelineStoreProvider");
  }
  return ctx;
}

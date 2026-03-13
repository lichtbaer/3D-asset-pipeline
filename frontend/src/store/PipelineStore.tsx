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
}

const PipelineStoreContext = createContext<PipelineStoreContextValue | null>(
  null
);

export function PipelineStoreProvider({ children }: { children: ReactNode }) {
  const [activeAssetId, setActiveAssetIdState] = useState<string | null>(null);
  const setActiveAssetId = useCallback((id: string | null) => {
    setActiveAssetIdState(id);
  }, []);

  return (
    <PipelineStoreContext.Provider
      value={{ activeAssetId, setActiveAssetId }}
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

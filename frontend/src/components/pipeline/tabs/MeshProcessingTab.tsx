import {
  MeshProcessingPanel,
  ProcessingResultsList,
} from "../../assets/MeshProcessingPanel.js";
import type { PipelineState } from "../../../hooks/usePipelineState.js";

interface MeshProcessingTabProps {
  state: PipelineState;
}

export function MeshProcessingTab({ state }: MeshProcessingTabProps) {
  return (
    <div className="pipeline-tab-content" role="tabpanel">
      <h1>Mesh-Processing</h1>
      <div className="pipeline-asset-context">
        {state.urlAssetId && state.urlAsset ? (
          <div className="pipeline-asset-context__loaded">
            <span>
              Aktuell geladen: Asset {state.urlAssetId.slice(0, 8)}…
            </span>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={state.clearAssetFromUrl}
            >
              ✕ Entfernen
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="btn btn--outline"
            onClick={() =>
              state.setAssetPickerOpen({ tab: "mesh-processing" })
            }
          >
            Aus Bibliothek laden
          </button>
        )}
      </div>
      {state.urlAssetId ? (
        <>
          <MeshProcessingPanel
            assetId={state.urlAssetId}
            textureBaking={state.urlAsset?.texture_baking ?? []}
            onUseForRigging={(url) => {
              state.setRiggingSourceGlbUrl(url);
              state.setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set("tab", "rigging");
                next.set("assetId", state.urlAssetId!);
                return next;
              });
            }}
          />
          {state.urlAsset?.processing && state.urlAsset.processing.length > 0 && (
            <ProcessingResultsList
              assetId={state.urlAssetId}
              processing={state.urlAsset.processing}
              onUseForRigging={(url) => {
                state.setRiggingSourceGlbUrl(url);
                state.setSearchParams((prev) => {
                  const next = new URLSearchParams(prev);
                  next.set("tab", "rigging");
                  next.set("assetId", state.urlAssetId!);
                  return next;
                });
              }}
            />
          )}
        </>
      ) : (
        <p className="pipeline-asset-context__empty">
          Wähle ein Asset aus der Bibliothek, um Mesh-Bearbeitung
          (Vereinfachen, Reparieren) durchzuführen.
        </p>
      )}
    </div>
  );
}

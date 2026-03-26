import { MeshForm } from "../MeshForm.js";
import { MeshJobStatus } from "../MeshJobStatus.js";
import { MeshJobHistory } from "../MeshJobHistory.js";
import { MeshCompareForm } from "../MeshCompareForm.js";
import { CompareResults } from "../CompareResults.js";
import { CompareHistory } from "../CompareHistory.js";
import { AssetUploadZone } from "../../assets/AssetUploadZone.js";
import { getAssetFileUrl } from "../../../api/assets.js";
import type { PipelineState } from "../../../hooks/usePipelineState.js";

interface MeshTabProps {
  state: PipelineState;
}

export function MeshTab({ state }: MeshTabProps) {
  return (
    <div className="pipeline-tab-content" role="tabpanel">
      <h1>Mesh-Generierung</h1>
      <div className="pipeline-mode-toggle" role="group" aria-label="Modus">
        <button
          type="button"
          className={`btn btn--ghost ${state.meshMode === "single" ? "pipeline-mode-toggle__btn--active" : ""}`}
          onClick={() => state.setMeshMode("single")}
        >
          Einzelgenerierung
        </button>
        <button
          type="button"
          className={`btn btn--ghost ${state.meshMode === "compare" ? "pipeline-mode-toggle__btn--active" : ""}`}
          onClick={() => state.setMeshMode("compare")}
        >
          Vergleich
        </button>
      </div>
      <section className="pipeline-page__form">
        <div className="pipeline-page__upload-row">
          <AssetUploadZone
            type="mesh"
            compact
            onSuccess={(assetId, file) => {
              state.setSearchParams({ tab: "rigging", assetId });
              state.setRiggingSourceGlbUrl(
                getAssetFileUrl(assetId, file ?? "mesh.glb")
              );
            }}
          />
          <span className="pipeline-page__upload-hint">
            oder Mesh aus Bild generieren:
          </span>
        </div>
        {state.meshMode === "single" ? (
          <MeshForm
            sourceImageUrl={state.meshSourceImageUrl}
            onSourceImageUrlChange={state.setMeshSourceImageUrl}
            providers={state.meshProviders}
            providersLoading={state.meshProvidersLoading}
            bgRemovalProviders={state.bgRemovalProviders}
            bgRemovalProvidersLoading={state.bgRemovalProvidersLoading}
            onSubmit={state.handleMeshSubmit}
            disabled={state.isMeshJobRunning}
          />
        ) : (
          <MeshCompareForm
            sourceImageUrl={state.meshSourceImageUrl}
            onSourceImageUrlChange={state.setMeshSourceImageUrl}
            meshProviders={state.meshProviders}
            meshProvidersLoading={state.meshProvidersLoading}
            onSubmit={state.handleCompareMeshSubmit}
            disabled={false}
          />
        )}
      </section>
      <section className="pipeline-page__status">
        {state.meshMode === "single" ? (
          <MeshJobStatus
            jobId={state.currentMeshJobId}
            onJobUpdate={state.handleMeshJobUpdate}
            onRetrySuccess={state.handleMeshRetrySuccess}
          />
        ) : (
          <CompareResults
            jobIdA={state.meshCompareJobIdA}
            jobIdB={state.meshCompareJobIdB}
            providerLabelA={state.meshCompareProviderLabelA}
            providerLabelB={state.meshCompareProviderLabelB}
            step="mesh"
            onRetrySuccessA={(id) => state.setMeshCompareJobIdA(id)}
            onRetrySuccessB={(id) => state.setMeshCompareJobIdB(id)}
          />
        )}
      </section>
      <section className="pipeline-page__history">
        {state.meshMode === "single" ? (
          <MeshJobHistory jobs={state.meshJobHistory} />
        ) : (
          <CompareHistory entries={state.meshCompareHistory} />
        )}
      </section>
    </div>
  );
}

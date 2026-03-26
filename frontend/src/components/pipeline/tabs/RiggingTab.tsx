import { RiggingForm } from "../rigging/RiggingForm.js";
import { RiggingJobStatus } from "../rigging/RiggingJobStatus.js";
import { RiggingJobHistory } from "../rigging/RiggingJobHistory.js";
import type { PipelineState } from "../../../hooks/usePipelineState.js";

interface RiggingTabProps {
  state: PipelineState;
}

export function RiggingTab({ state }: RiggingTabProps) {
  return (
    <div className="pipeline-tab-content" role="tabpanel">
      <h1>Rigging</h1>
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
              state.setAssetPickerOpen({ tab: "rigging" })
            }
          >
            Aus Bibliothek laden
          </button>
        )}
      </div>
      <section className="pipeline-page__form">
        <RiggingForm
          sourceGlbUrl={state.riggingSourceGlbUrl}
          onSourceGlbUrlChange={state.setRiggingSourceGlbUrl}
          providers={state.riggingProviders}
          providersLoading={state.riggingProvidersLoading}
          onSubmit={state.handleRiggingSubmit}
          disabled={state.isRiggingJobRunning}
          assetId={state.activeAssetId}
          availableMeshFiles={state.riggingMeshFiles}
        />
      </section>
      <section className="pipeline-page__status">
        <RiggingJobStatus
          jobId={state.currentRiggingJobId}
          onJobUpdate={state.handleRiggingJobUpdate}
          onRetrySuccess={state.handleRiggingRetrySuccess}
        />
      </section>
      <section className="pipeline-page__history">
        <RiggingJobHistory
          jobs={state.riggingJobHistory}
          onSelectJob={state.handleRiggingJobSelect}
        />
      </section>
    </div>
  );
}

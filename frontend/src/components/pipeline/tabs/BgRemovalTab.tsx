import { BgRemovalForm } from "../BgRemovalForm.js";
import { BgRemovalJobStatus } from "../BgRemovalJobStatus.js";
import { BgRemovalJobHistory } from "../BgRemovalJobHistory.js";
import { ImageEditor } from "../ImageEditor.js";
import type { PipelineState } from "../../../hooks/usePipelineState.js";

interface BgRemovalTabProps {
  state: PipelineState;
}

export function BgRemovalTab({ state }: BgRemovalTabProps) {
  return (
    <div className="pipeline-tab-content" role="tabpanel">
      <h1>Freistellung</h1>
      <section className="pipeline-page__form">
        <BgRemovalForm
          sourceImageUrl={state.bgRemovalSourceImageUrl}
          onSourceImageUrlChange={state.setBgRemovalSourceImageUrl}
          providers={state.bgRemovalProviders}
          providersLoading={state.bgRemovalProvidersLoading}
          onSubmit={state.handleBgRemovalSubmit}
          disabled={state.isBgRemovalJobRunning}
        />
      </section>
      <section className="pipeline-page__status">
        <BgRemovalJobStatus
          jobId={state.currentBgRemovalJobId}
          onJobUpdate={state.handleBgRemovalJobUpdate}
          onUseForMesh={state.handleUseForMesh}
          onRetrySuccess={state.handleBgRemovalRetrySuccess}
          hideUseForMesh={
            !!(
              state.urlAssetId ||
              (state.currentBgRemovalJob?.status === "done" &&
                state.currentBgRemovalJob?.asset_id)
            )
          }
        />
      </section>
      <section className="pipeline-page__history">
        <BgRemovalJobHistory
          jobs={state.bgRemovalJobHistory}
          onUseForMesh={state.handleUseForMesh}
          hideUseForMeshForAssetIds={
            state.urlAssetId ||
            (state.currentBgRemovalJob?.status === "done" &&
              state.currentBgRemovalJob?.asset_id)
              ? [
                  ...new Set([
                    ...(state.currentBgRemovalJob?.asset_id
                      ? [state.currentBgRemovalJob.asset_id]
                      : []),
                    ...(state.urlAssetId ? [state.urlAssetId] : []),
                  ]),
                ]
              : []
          }
        />
      </section>
      {(state.urlAssetId ||
        (state.currentBgRemovalJob?.status === "done" &&
          state.currentBgRemovalJob?.asset_id)) && (
        <ImageEditor
          assetId={
            state.urlAssetId ?? state.currentBgRemovalJob?.asset_id ?? ""
          }
          onUseForMesh={state.handleUseForMesh}
        />
      )}
    </div>
  );
}

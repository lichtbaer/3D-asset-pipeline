import { AnimationForm } from "../animation/AnimationForm.js";
import { AnimationJobStatus } from "../animation/AnimationJobStatus.js";
import { AnimationJobHistory } from "../animation/AnimationJobHistory.js";
import type { PipelineState } from "../../../hooks/usePipelineState.js";

interface AnimationTabProps {
  state: PipelineState;
}

export function AnimationTab({ state }: AnimationTabProps) {
  return (
    <div className="pipeline-tab-content" role="tabpanel">
      <h1>Animation</h1>
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
              state.setAssetPickerOpen({ tab: "animation" })
            }
          >
            Aus Bibliothek laden
          </button>
        )}
      </div>
      <section className="pipeline-page__form">
        <AnimationForm
          sourceGlbUrl={state.animationSourceGlbUrl}
          onSourceGlbUrlChange={state.setAnimationSourceGlbUrl}
          providers={state.animationProviders}
          providersLoading={state.animationProvidersLoading}
          onSubmit={state.handleAnimationSubmit}
          disabled={state.isAnimationJobRunning}
        />
      </section>
      <section className="pipeline-page__status">
        <AnimationJobStatus
          jobId={state.currentAnimationJobId}
          onJobUpdate={state.handleAnimationJobUpdate}
          onRetrySuccess={state.handleAnimationRetrySuccess}
          onTryDifferentPreset={state.handleTryDifferentPreset}
        />
      </section>
      <section className="pipeline-page__history">
        <AnimationJobHistory jobs={state.animationJobHistory} />
      </section>
    </div>
  );
}

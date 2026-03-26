import { PromptForm } from "../../generation/PromptForm.js";
import { JobStatus } from "../../generation/JobStatus.js";
import { JobHistory } from "../../generation/JobHistory.js";
import { ImageCompareForm } from "../ImageCompareForm.js";
import { CompareResults } from "../CompareResults.js";
import { CompareHistory } from "../CompareHistory.js";
import { AssetUploadZone } from "../../assets/AssetUploadZone.js";
import { getAssetFileUrl } from "../../../api/assets.js";
import type { PipelineState } from "../../../hooks/usePipelineState.js";

interface ImageTabProps {
  state: PipelineState;
}

export function ImageTab({ state }: ImageTabProps) {
  return (
    <div className="pipeline-tab-content" role="tabpanel">
      <h1>Bildgenerierung</h1>
      {state.sketchfabEnabled?.enabled && (
        <p className="pipeline-tab__sketchfab-link">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => state.setShowSketchfabImport(true)}
          >
            Von Sketchfab importieren
          </button>
        </p>
      )}
      <div className="pipeline-mode-toggle" role="group" aria-label="Modus">
        <button
          type="button"
          className={`btn btn--ghost ${state.imageMode === "single" ? "pipeline-mode-toggle__btn--active" : ""}`}
          onClick={() => state.setImageMode("single")}
        >
          Einzelgenerierung
        </button>
        <button
          type="button"
          className={`btn btn--ghost ${state.imageMode === "compare" ? "pipeline-mode-toggle__btn--active" : ""}`}
          onClick={() => state.setImageMode("compare")}
        >
          Vergleich
        </button>
      </div>
      <section className="pipeline-page__form">
        <div className="pipeline-page__upload-row">
          <AssetUploadZone
            type="image"
            compact
            onSuccess={(assetId, file) => {
              state.setSearchParams({ tab: "bgremoval", assetId });
              state.setBgRemovalSourceImageUrl(
                getAssetFileUrl(assetId, file ?? "image_original.png")
              );
            }}
          />
          <span className="pipeline-page__upload-hint">
            oder Bild generieren:
          </span>
        </div>
        {state.imageMode === "single" ? (
          <PromptForm
            models={state.models}
            modelsLoading={state.modelsLoading}
            onSubmit={state.handleImageSubmit}
            disabled={state.isImageJobRunning}
          />
        ) : (
          <ImageCompareForm
            imageProviders={state.imageProviders}
            imageProvidersLoading={state.imageProvidersLoading}
            onSubmit={state.handleCompareImageSubmit}
            disabled={false}
          />
        )}
      </section>
      <section className="pipeline-page__status">
        {state.imageMode === "single" ? (
          <JobStatus
            jobId={state.currentImageJobId}
            onJobUpdate={state.handleImageJobUpdate}
            onRetrySuccess={state.handleImageRetrySuccess}
          />
        ) : (
          <CompareResults
            jobIdA={state.imageCompareJobIdA}
            jobIdB={state.imageCompareJobIdB}
            providerLabelA={state.imageCompareProviderLabelA}
            providerLabelB={state.imageCompareProviderLabelB}
            step="image"
            onUseForMesh={state.handleCompareUseForMesh}
            onUseForBgRemoval={state.handleCompareUseForBgRemoval}
            onRetrySuccessA={(id) => state.setImageCompareJobIdA(id)}
            onRetrySuccessB={(id) => state.setImageCompareJobIdB(id)}
          />
        )}
      </section>
      <section className="pipeline-page__history">
        {state.imageMode === "single" ? (
          <JobHistory
            jobs={state.imageJobHistory}
            onUseForMesh={state.handleUseForMesh}
            onUseForBgRemoval={state.handleUseForBgRemoval}
          />
        ) : (
          <CompareHistory entries={state.imageCompareHistory} />
        )}
      </section>
    </div>
  );
}

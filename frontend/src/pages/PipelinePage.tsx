import { useState } from "react";
import { usePipelineState, type TabId } from "../hooks/usePipelineState.js";
import { PipelineStepper } from "../components/ui/PipelineStepper.js";
import { AssetPickerModal } from "../components/assets/AssetPickerModal.js";
import { SketchfabImportModal } from "../components/assets/SketchfabImportModal.js";
import { ImageTab } from "../components/pipeline/tabs/ImageTab.js";
import { BgRemovalTab } from "../components/pipeline/tabs/BgRemovalTab.js";
import { MeshTab } from "../components/pipeline/tabs/MeshTab.js";
import { RiggingTab } from "../components/pipeline/tabs/RiggingTab.js";
import { AnimationTab } from "../components/pipeline/tabs/AnimationTab.js";
import { MeshProcessingTab } from "../components/pipeline/tabs/MeshProcessingTab.js";
import { AutoPipelinePanel } from "../components/pipeline/AutoPipelinePanel.js";
import "./ImageGenerationPage.css";
import "./PipelinePage.css";

export type { TabId };

type PipelineMode = "manual" | "auto";

export function PipelinePage() {
  const state = usePipelineState();
  const [pipelineMode, setPipelineMode] = useState<PipelineMode>("manual");

  return (
    <main className="pipeline-page">
      <div className="pipeline-mode-toggle pipeline-mode-toggle--page" role="group" aria-label="Pipeline-Modus">
        <button
          type="button"
          className={`btn btn--ghost ${pipelineMode === "manual" ? "pipeline-mode-toggle__btn--active" : ""}`}
          onClick={() => setPipelineMode("manual")}
        >
          Manuell
        </button>
        <button
          type="button"
          className={`btn btn--ghost ${pipelineMode === "auto" ? "pipeline-mode-toggle__btn--active" : ""}`}
          onClick={() => setPipelineMode("auto")}
        >
          Auto-Pipeline
        </button>
      </div>

      {pipelineMode === "auto" && (
        <div className="pipeline-page__auto">
          <AutoPipelinePanel />
        </div>
      )}

      {pipelineMode === "manual" && (
        <>
          <PipelineStepper steps={state.pipelineSteps} onStepClick={(id) => state.setActiveTab(id as TabId)} />

          {state.activeTab === "image" && <ImageTab state={state} />}
          {state.activeTab === "bgremoval" && <BgRemovalTab state={state} />}
          {state.activeTab === "mesh" && <MeshTab state={state} />}
          {state.activeTab === "rigging" && <RiggingTab state={state} />}
          {state.activeTab === "animation" && <AnimationTab state={state} />}
          {state.activeTab === "mesh-processing" && <MeshProcessingTab state={state} />}

          {state.assetPickerOpen && (
            <AssetPickerModal
              isOpen={true}
              onClose={() => state.setAssetPickerOpen(null)}
              onSelect={(asset) =>
                state.handleAssetPickerSelect(asset, state.assetPickerOpen!.tab)
              }
              filter={
                state.assetPickerOpen.tab === "animation" ? "has_rigging" : "has_mesh"
              }
            />
          )}
          {state.showSketchfabImport && (
            <SketchfabImportModal onClose={() => state.setShowSketchfabImport(false)} />
          )}
        </>
      )}
    </main>
  );
}

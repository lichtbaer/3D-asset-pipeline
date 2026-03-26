import { getAssetFileUrl, type AssetDetail } from "../../api/assets.js";
import { MeshViewer } from "../viewer/MeshViewer.js";
import { ImageProcessingList } from "./ImageProcessingList.js";
import { ImageEditor } from "../pipeline/ImageEditor.js";

export interface AssetFilesPreviewsProps {
  data: AssetDetail;
  steps: AssetDetail["steps"];
  hasImage: boolean;
  hasBgremoval: boolean;
  hasMesh: boolean;
  hasRigging: boolean;
  hasAnimation: boolean;
  imageFile: string | null;
  bgremovalFile: string | null;
  imageUrl: string | null;
  bgremovalUrl: string | null;
  meshUrl: string | null;
  riggedUrl: string | null;
  animationFile: string | null;
  animationUrl: string | null;
  motionPrompt: string | undefined;
  handleStepDeleteClick: (
    step: "image" | "bgremoval" | "mesh" | "rigging" | "animation",
    stepLabel: string
  ) => void;
  handleAction: (
    tab: "bgremoval" | "mesh" | "rigging" | "animation" | "mesh-processing",
    sourceUrl: string,
    assetIdForJob: string
  ) => void;
}

export function AssetFilesPreviews({
  data,
  hasImage,
  hasBgremoval,
  hasMesh,
  hasRigging,
  hasAnimation,
  imageFile,
  bgremovalFile,
  meshUrl,
  riggedUrl,
  animationFile,
  animationUrl,
  motionPrompt,
  handleStepDeleteClick,
  handleAction,
}: AssetFilesPreviewsProps) {
  return (
    <section className="asset-modal__files">
      <h3>Dateien</h3>
      <div className="asset-modal__previews">
        {hasImage && imageFile && (
          <div className="asset-modal__preview-item asset-modal__step-block">
            <img
              src={getAssetFileUrl(data.asset_id, imageFile)}
              alt="Originalbild"
              className="asset-modal__preview-img"
            />
            <p className="asset-modal__preview-label">Bild (Original)</p>
            <a
              href={getAssetFileUrl(data.asset_id, imageFile)}
              download
              className="asset-modal__download"
            >
              Download
            </a>
            <button
              type="button"
              className="asset-modal__step-delete"
              onClick={() => handleStepDeleteClick("image", "Bild")}
            >
              Step löschen
            </button>
          </div>
        )}
        {hasBgremoval && bgremovalFile && (
          <div className="asset-modal__preview-item asset-modal__step-block">
            <div className="asset-modal__checkerboard">
              <img
                src={getAssetFileUrl(data.asset_id, bgremovalFile)}
                alt="Freigestellt"
                className="asset-modal__preview-img"
              />
            </div>
            <p className="asset-modal__preview-label">Freigestellt</p>
            <a
              href={getAssetFileUrl(data.asset_id, bgremovalFile)}
              download
              className="asset-modal__download"
            >
              Download
            </a>
            <button
              type="button"
              className="asset-modal__step-delete"
              onClick={() => handleStepDeleteClick("bgremoval", "Freistellung")}
            >
              Step löschen
            </button>
          </div>
        )}
        {hasMesh && meshUrl && (
          <div className="asset-modal__preview-item asset-modal__step-block">
            <MeshViewer glbUrl={meshUrl} height={450} />
            <p className="asset-modal__preview-label">mesh.glb</p>
            <a
              href={meshUrl}
              download
              className="asset-modal__download"
            >
              Download GLB
            </a>
            <button
              type="button"
              className="asset-modal__step-delete"
              onClick={() => handleStepDeleteClick("mesh", "Mesh")}
            >
              Step löschen
            </button>
          </div>
        )}
        {hasRigging && riggedUrl && (
          <div className="asset-modal__preview-item asset-modal__step-block">
            <MeshViewer glbUrl={riggedUrl} height={450} />
            <p className="asset-modal__preview-label">mesh_rigged.glb</p>
            <a
              href={riggedUrl}
              download
              className="asset-modal__download"
            >
              Download rigged GLB
            </a>
            <button
              type="button"
              className="asset-modal__step-delete"
              onClick={() => handleStepDeleteClick("rigging", "Rigging")}
            >
              Step löschen
            </button>
          </div>
        )}
        {hasAnimation && animationUrl && (
          <div className="asset-modal__preview-item asset-modal__step-block">
            <p className="asset-modal__preview-label">🎬 Animation</p>
            {motionPrompt && (
              <p className="asset-modal__motion-prompt">
                Motion: {motionPrompt}
              </p>
            )}
            <a
              href={animationUrl}
              download
              className="asset-modal__download"
            >
              Download {animationFile ?? "Animation"}
            </a>
            <button
              type="button"
              className="asset-modal__step-delete"
              onClick={() => handleStepDeleteClick("animation", "Animation")}
            >
              Step löschen
            </button>
          </div>
        )}
      </div>
      {(data.image_processing?.length ?? 0) > 0 && (
        <ImageProcessingList
          assetId={data.asset_id}
          imageProcessing={data.image_processing ?? []}
        />
      )}
      {(hasImage || hasBgremoval) && (
        <ImageEditor
          assetId={data.asset_id}
          onUseForMesh={(imageUrl) =>
            handleAction("mesh", imageUrl, data.asset_id)
          }
        />
      )}
    </section>
  );
}

import { getAssetFileUrl, type AssetDetail, type AssetStepData } from "../../api/assets.js";

export interface AssetPipelineActionsProps {
  data: AssetDetail;
  steps: Record<string, AssetStepData>;
  hasImage: boolean;
  hasBgremoval: boolean;
  hasMesh: boolean;
  hasRigging: boolean;
  hasAnimation: boolean;
  imageUrl: string | null;
  bgremovalUrl: string | null;
  meshUrl: string | null;
  handleAction: (
    tab: "bgremoval" | "mesh" | "rigging" | "animation" | "mesh-processing",
    sourceUrl: string,
    assetIdForJob: string
  ) => void;
}

export function AssetPipelineActions({
  data,
  steps,
  hasImage,
  hasBgremoval,
  hasMesh,
  hasRigging,
  hasAnimation,
  imageUrl,
  bgremovalUrl,
  meshUrl,
  handleAction,
}: AssetPipelineActionsProps) {
  return (
    <section className="asset-modal__actions">
      <h3>Pipeline-Weiterführung</h3>
      <div className="asset-modal__action-buttons">
        {hasImage && imageUrl && !hasBgremoval && (
          <button
            type="button"
            className="btn btn--outline"
            onClick={() =>
              handleAction("bgremoval", imageUrl, data.asset_id)
            }
          >
            → Freistellen
          </button>
        )}
        {(hasImage || hasBgremoval) &&
          !hasMesh &&
          (bgremovalUrl ?? imageUrl) && (
            <button
              type="button"
              className="btn btn--outline"
              onClick={() =>
                handleAction(
                  "mesh",
                  bgremovalUrl ?? imageUrl ?? "",
                  data.asset_id
                )
              }
            >
              → Als Mesh-Input
            </button>
          )}
        {hasMesh && (
          <>
            <button
              type="button"
              className="btn btn--outline"
              onClick={() =>
                handleAction("rigging", meshUrl ?? "", data.asset_id)
              }
            >
              → Riggen
            </button>
            <button
              type="button"
              className="btn btn--outline"
              onClick={() =>
                handleAction("mesh-processing", meshUrl ?? "", data.asset_id)
              }
            >
              → Mesh-Processing
            </button>
          </>
        )}
        {hasRigging && (
          <>
            <button
              type="button"
              className="btn btn--outline"
              onClick={() => {
                const glbUrl =
                  steps.rigging && "file" in steps.rigging
                    ? getAssetFileUrl(
                        data.asset_id,
                        String(steps.rigging.file)
                      )
                    : meshUrl ?? "";
                if (glbUrl) {
                  handleAction("animation", glbUrl, data.asset_id);
                }
              }}
            >
              → Animieren
            </button>
            <button
              type="button"
              className="btn btn--outline"
              onClick={() =>
                handleAction("rigging", meshUrl ?? "", data.asset_id)
              }
            >
              → Riggen (erneut)
            </button>
          </>
        )}
        {hasImage &&
          hasBgremoval &&
          hasMesh &&
          (hasRigging || hasAnimation) && (
            <p className="asset-modal__all-done">
              Alle Schritte vorhanden. Nutze die Download-Links oben.
            </p>
          )}
      </div>
    </section>
  );
}

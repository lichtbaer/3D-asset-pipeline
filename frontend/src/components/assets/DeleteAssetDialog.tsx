import type { AssetListItem } from "../../api/assets.js";

interface DeleteAssetDialogProps {
  asset: AssetListItem | null;
  assetCount?: number;
  mode: "single" | "batch" | "purge";
  purgeCount?: number;
  purgeSize?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function getAssetDisplayName(asset: AssetListItem): string {
  const imageStep = asset.steps?.image as { name?: string } | undefined;
  const meshStep = asset.steps?.mesh as { name?: string } | undefined;
  return imageStep?.name ?? meshStep?.name ?? `Asset ${asset.asset_id.slice(0, 8)}`;
}

export function DeleteAssetDialog({
  asset,
  assetCount = 0,
  mode,
  purgeCount = 0,
  purgeSize = "0 B",
  onConfirm,
  onCancel,
}: DeleteAssetDialogProps) {
  const content =
    mode === "single" && asset ? (
      <>
        <h2 id="delete-dialog-title">Asset löschen?</h2>
        <p>
          &quot;{getAssetDisplayName(asset)}&quot; wird in den Papierkorb
          verschoben. Alle zugehörigen Files (Mesh, Rig, Exports) bleiben
          erhalten, bis der Papierkorb geleert wird.
        </p>
        <div className="delete-dialog__actions">
          <button type="button" className="btn btn--outline" onClick={onCancel}>
            Abbrechen
          </button>
          <button type="button" className="btn btn--primary" onClick={onConfirm}>
            In Papierkorb
          </button>
        </div>
      </>
    ) : mode === "batch" && assetCount > 0 ? (
      <>
        <h2 id="delete-dialog-title">{assetCount} Assets löschen?</h2>
        <p>
          {assetCount} Asset{assetCount > 1 ? "s" : ""} werden in den Papierkorb
          verschoben.
        </p>
        <div className="delete-dialog__actions">
          <button type="button" className="btn btn--outline" onClick={onCancel}>
            Abbrechen
          </button>
          <button type="button" className="btn btn--primary" onClick={onConfirm}>
            In Papierkorb
          </button>
        </div>
      </>
    ) : mode === "purge" && purgeCount > 0 ? (
      <>
        <h2 id="delete-dialog-title">Papierkorb leeren?</h2>
        <p>
          {purgeCount} Asset{purgeCount > 1 ? "s" : ""} ({purgeSize}) werden
          unwiderruflich gelöscht.
        </p>
        <div className="delete-dialog__actions">
          <button type="button" className="btn btn--outline" onClick={onCancel}>
            Abbrechen
          </button>
          <button
            type="button"
            className="btn btn--primary btn--danger"
            onClick={onConfirm}
          >
            Papierkorb leeren
          </button>
        </div>
      </>
    ) : null;

  if (!content) return null;

  return (
    <div className="delete-dialog-overlay" onClick={onCancel}>
      <div
        className="delete-dialog"
        role="dialog"
        aria-labelledby="delete-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        {content}
      </div>
    </div>
  );
}

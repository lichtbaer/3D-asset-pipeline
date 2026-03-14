import type { AssetListItem } from "../../api/assets.js";

interface TrashActionsDialogProps {
  asset: AssetListItem;
  onRestore: () => void;
  onPermanentDelete: () => void;
  onCancel: () => void;
}

function getAssetDisplayName(asset: AssetListItem): string {
  const imageStep = asset.steps?.image as { name?: string } | undefined;
  const meshStep = asset.steps?.mesh as { name?: string } | undefined;
  return imageStep?.name ?? meshStep?.name ?? asset.asset_id.slice(0, 8);
}

export function TrashActionsDialog({
  asset,
  onRestore,
  onPermanentDelete,
  onCancel,
}: TrashActionsDialogProps) {
  const name = getAssetDisplayName(asset);
  return (
    <div className="delete-dialog" role="dialog" aria-labelledby="trash-dialog-title" onClick={(e) => e.stopPropagation()}>
      <h2 id="trash-dialog-title">Papierkorb: {name}</h2>
      <p>Dieses Asset ist im Papierkorb. Sie können es wiederherstellen oder permanent löschen.</p>
      <div className="delete-dialog__actions">
        <button type="button" className="btn btn--outline" onClick={onCancel}>
          Schließen
        </button>
        <button type="button" className="btn btn--outline" onClick={onRestore}>
          Wiederherstellen
        </button>
        <button type="button" className="btn btn--primary btn--danger" onClick={onPermanentDelete}>
          Permanent löschen
        </button>
      </div>
    </div>
  );
}

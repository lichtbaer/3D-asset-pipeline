import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAsset, getAssetFileUrl } from "../../api/assets.js";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("de-DE");
  } catch {
    return iso;
  }
}

export function AssetDetail() {
  const { assetId } = useParams<{ assetId: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => getAsset(assetId!),
    enabled: !!assetId,
  });

  if (!assetId) {
    return (
      <div className="asset-detail">
        <p>Kein Asset ausgewählt.</p>
      </div>
    );
  }

  if (isLoading && !data) {
    return (
      <div className="asset-detail asset-detail--loading">
        <div className="spinner" aria-hidden />
        <p>Asset wird geladen...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="asset-detail asset-detail--error">
        <p>
          Fehler beim Laden:{" "}
          {error instanceof Error ? error.message : "Unbekannter Fehler"}
        </p>
      </div>
    );
  }

  const { steps } = data;
  const hasImage = "image" in steps;
  const hasBgremoval = "bgremoval" in steps;
  const hasMesh = "mesh" in steps;

  return (
    <div className="asset-detail">
      <header className="asset-detail__header">
        <Link to="/assets" className="asset-detail__back">
          ← Zurück zur Bibliothek
        </Link>
        <h1>Asset {data.asset_id.slice(0, 8)}…</h1>
        <p className="asset-detail__dates">
          Erstellt: {formatDate(data.created_at)} · Aktualisiert:{" "}
          {formatDate(data.updated_at)}
        </p>
      </header>

      <section className="asset-detail__files">
        <h2>Dateien</h2>
        <div className="asset-detail__previews">
          {hasImage && steps.image && "file" in steps.image && (
            <div className="asset-detail__preview-item">
              <img
                src={getAssetFileUrl(
                  data.asset_id,
                  String(steps.image.file)
                )}
                alt="Originalbild"
                className="asset-detail__preview-img"
              />
              <p className="asset-detail__preview-label">Bild (Original)</p>
              <a
                href={getAssetFileUrl(
                  data.asset_id,
                  String(steps.image.file)
                )}
                download
                className="asset-detail__download"
              >
                Download
              </a>
            </div>
          )}
          {hasBgremoval && steps.bgremoval && "file" in steps.bgremoval && (
            <div className="asset-detail__preview-item">
              <img
                src={getAssetFileUrl(
                  data.asset_id,
                  String(steps.bgremoval.file)
                )}
                alt="Freigestellt"
                className="asset-detail__preview-img"
              />
              <p className="asset-detail__preview-label">Freigestellt</p>
              <a
                href={getAssetFileUrl(
                  data.asset_id,
                  String(steps.bgremoval.file)
                )}
                download
                className="asset-detail__download"
              >
                Download
              </a>
            </div>
          )}
          {hasMesh && steps.mesh && "file" in steps.mesh && (
            <div className="asset-detail__preview-item">
              <div className="asset-detail__mesh-placeholder">
                <span>3D-Mesh</span>
              </div>
              <p className="asset-detail__preview-label">mesh.glb</p>
              <a
                href={getAssetFileUrl(
                  data.asset_id,
                  String(steps.mesh.file)
                )}
                download
                className="asset-detail__download"
              >
                Download GLB
              </a>
            </div>
          )}
        </div>
      </section>

      <section className="asset-detail__meta">
        <h2>Metadaten</h2>
        <pre className="asset-detail__meta-json">
          {JSON.stringify(data.steps, null, 2)}
        </pre>
      </section>

      <section className="asset-detail__actions">
        <h2>Als Input verwenden</h2>
        <div className="asset-detail__action-buttons">
          {hasImage && steps.image && "file" in steps.image && (
            <Link
              to={`/pipeline?tab=bgremoval&source=${encodeURIComponent(
                getAssetFileUrl(data.asset_id, String(steps.image.file))
              )}`}
              className="asset-detail__action-btn"
            >
              → Freistellen
            </Link>
          )}
          {(hasImage || hasBgremoval) && (
            <Link
              to={`/pipeline?tab=mesh&source=${encodeURIComponent(
                getAssetFileUrl(
                  data.asset_id,
                  hasBgremoval && steps.bgremoval && "file" in steps.bgremoval
                    ? String(steps.bgremoval.file)
                    : steps.image && "file" in steps.image
                      ? String(steps.image.file)
                      : "image_original.png"
                )
              )}`}
              className="asset-detail__action-btn"
            >
              → Als Mesh-Input verwenden
            </Link>
          )}
        </div>
      </section>
    </div>
  );
}

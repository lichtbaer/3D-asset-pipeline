import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getStorageStats, purgeDeleted } from "../api/storage.js";
import { DeleteAssetDialog } from "../components/assets/DeleteAssetDialog.js";

const BREAKDOWN_LABELS: Record<string, string> = {
  images: "Bilder",
  meshes: "Meshes",
  rigs: "Rigs",
  animations: "Animationen",
  exports: "Exports",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export function StoragePage() {
  const queryClient = useQueryClient();
  const [showPurgeDialog, setShowPurgeDialog] = useState(false);

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ["storage"],
    queryFn: getStorageStats,
  });

  const handlePurgeConfirm = async () => {
    await purgeDeleted();
    setShowPurgeDialog(false);
    void queryClient.invalidateQueries({ queryKey: ["storage"] });
    void queryClient.invalidateQueries({ queryKey: ["assets"] });
  };

  if (isLoading && !stats) {
    return (
      <main className="storage-page">
        <div className="storage-page__loading">
          <div className="spinner" aria-hidden />
          <p>Speicherstatistik wird geladen...</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="storage-page">
        <div className="storage-page__error">
          <p>
            Fehler: {error instanceof Error ? error.message : "Unbekannter Fehler"}
          </p>
        </div>
      </main>
    );
  }

  const maxBreakdownSize = stats
    ? Math.max(
        ...Object.values(stats.breakdown).map((b) => b.size_bytes),
        1
      )
    : 1;

  return (
    <main className="storage-page">
      <header className="storage-page__header">
        <h1>Speicherverbrauch</h1>
        <p className="storage-page__subtitle">
          Übersicht über den Speicherbedarf Ihrer Assets
        </p>
        <Link to="/assets" className="storage-page__back">
          ← Zur Bibliothek
        </Link>
      </header>

      {stats && (
        <>
          <div className="storage-page__summary">
            <div className="storage-page__summary-item">
              <span className="storage-page__summary-label">Gesamt</span>
              <span className="storage-page__summary-value">
                {stats.total_size_human}
              </span>
            </div>
            <div className="storage-page__summary-item">
              <span className="storage-page__summary-label">Assets</span>
              <span className="storage-page__summary-value">
                {stats.asset_count}
              </span>
            </div>
            <div className="storage-page__summary-item">
              <span className="storage-page__summary-label">Gelöscht</span>
              <span className="storage-page__summary-value">
                {stats.deleted_count}
              </span>
            </div>
          </div>

          <div className="storage-page__breakdown">
            <h2>Breakdown nach Typ</h2>
            {Object.entries(stats.breakdown).map(([key, item]) => {
              const pct = maxBreakdownSize > 0 ? (item.size_bytes / maxBreakdownSize) * 100 : 0;
              return (
                <div key={key} className="storage-page__breakdown-row">
                  <div className="storage-page__breakdown-bar-wrap">
                    <div
                      className="storage-page__breakdown-bar"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="storage-page__breakdown-label">
                    {BREAKDOWN_LABELS[key] ?? key}
                  </span>
                  <span className="storage-page__breakdown-size">
                    {formatBytes(item.size_bytes)}
                  </span>
                  <span className="storage-page__breakdown-count">
                    {item.count} Assets
                  </span>
                </div>
              );
            })}
          </div>

          <div className="storage-page__trash">
            <h2>Papierkorb</h2>
            <p>
              {formatBytes(stats.deleted_size_bytes)} ({stats.deleted_count}{" "}
              Assets)
            </p>
            <button
              type="button"
              className="btn btn--outline"
              disabled={stats.deleted_count === 0}
              onClick={() => setShowPurgeDialog(true)}
            >
              Papierkorb leeren
            </button>
          </div>
        </>
      )}

      {showPurgeDialog && stats && stats.deleted_count > 0 && (
        <DeleteAssetDialog
          asset={null}
          mode="purge"
          purgeCount={stats.deleted_count}
          purgeSize={formatBytes(stats.deleted_size_bytes)}
          onConfirm={handlePurgeConfirm}
          onCancel={() => setShowPurgeDialog(false)}
        />
      )}
    </main>
  );
}

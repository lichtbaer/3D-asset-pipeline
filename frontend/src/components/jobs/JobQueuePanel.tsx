import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listJobs } from "../../api/generation.js";
import type { JobListItem } from "../../api/generation.js";

type StatusFilter = "all" | "processing" | "failed" | "done" | "pending";

const STATUS_LABELS: Record<string, string> = {
  pending: "Wartend",
  processing: "Läuft",
  done: "Fertig",
  failed: "Fehler",
};

const JOB_TYPE_LABELS: Record<string, string> = {
  image: "Bild",
  bgremoval: "BG-Entfernung",
  mesh: "Mesh",
  rigging: "Rigging",
  animation: "Animation",
  texture_baking: "Textur-Bake",
};

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString("de-DE", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "done"
      ? "job-queue__badge job-queue__badge--done"
      : status === "failed"
      ? "job-queue__badge job-queue__badge--failed"
      : status === "processing"
      ? "job-queue__badge job-queue__badge--processing"
      : "job-queue__badge job-queue__badge--pending";
  return <span className={cls}>{STATUS_LABELS[status] ?? status}</span>;
}

export function JobQueuePanel() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(0);
  const limit = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["jobs", statusFilter, page],
    queryFn: () =>
      listJobs({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit,
        offset: page * limit,
      }),
    refetchInterval: 10_000,
  });

  const filters: StatusFilter[] = ["all", "processing", "failed", "pending", "done"];
  const filterLabels: Record<StatusFilter, string> = {
    all: "Alle",
    processing: "Läuft",
    failed: "Fehler",
    pending: "Wartend",
    done: "Fertig",
  };

  function handleFilterChange(f: StatusFilter) {
    setStatusFilter(f);
    setPage(0);
  }

  const totalPages = data ? Math.ceil(data.total / limit) : 0;

  return (
    <section className="job-queue-panel">
      <h2>Job-Queue</h2>
      <p className="job-queue-panel__subtitle">
        Alle Generierungsjobs quer über alle Assets
      </p>

      <div className="job-queue-panel__filters" role="group" aria-label="Status-Filter">
        {filters.map((f) => (
          <button
            key={f}
            type="button"
            className={`btn btn--ghost btn--sm ${statusFilter === f ? "job-queue-panel__filter--active" : ""}`}
            onClick={() => handleFilterChange(f)}
          >
            {filterLabels[f]}
          </button>
        ))}
      </div>

      {isLoading && !data ? (
        <div className="job-queue-panel__loading">
          <div className="spinner" aria-hidden />
          <p>Wird geladen…</p>
        </div>
      ) : (
        <>
          <div className="job-queue-panel__count">
            {data?.total ?? 0} Jobs gesamt
          </div>
          <div className="job-queue-panel__table-wrap">
            <table className="job-queue-panel__table">
              <thead>
                <tr>
                  <th>Typ</th>
                  <th>Status</th>
                  <th>Provider</th>
                  <th>Asset</th>
                  <th>Erstellt</th>
                  <th>Fehler</th>
                </tr>
              </thead>
              <tbody>
                {data?.jobs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="job-queue-panel__empty">
                      Keine Jobs gefunden
                    </td>
                  </tr>
                )}
                {data?.jobs.map((job: JobListItem) => (
                  <tr key={job.job_id} className={job.status === "failed" ? "job-queue-panel__row--failed" : ""}>
                    <td>{JOB_TYPE_LABELS[job.job_type] ?? job.job_type}</td>
                    <td><StatusBadge status={job.status} /></td>
                    <td className="job-queue-panel__provider">{job.provider_key}</td>
                    <td>
                      {job.asset_id ? (
                        <Link to={`/assets/${job.asset_id}`} className="job-queue-panel__asset-link">
                          {job.asset_id.slice(0, 8)}…
                        </Link>
                      ) : (
                        <span className="job-queue-panel__no-asset">—</span>
                      )}
                    </td>
                    <td className="job-queue-panel__date">{formatDate(job.created_at)}</td>
                    <td className="job-queue-panel__error">
                      {job.error_type ? (
                        <code title={job.error_type}>{job.error_type.slice(0, 30)}</code>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="job-queue-panel__pagination">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setPage((p) => p - 1)}
                disabled={page === 0}
              >
                Zurück
              </button>
              <span>
                Seite {page + 1} / {totalPages}
              </span>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= totalPages - 1}
              >
                Weiter
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

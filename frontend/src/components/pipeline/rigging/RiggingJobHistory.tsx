export interface RiggingJobHistoryEntry {
  job_id: string;
  source_glb_url: string;
  provider_key: string;
  status: string;
  result_url: string | null;
  asset_id?: string | null;
  created_at?: string;
}

export interface RiggingJobHistoryProps {
  jobs: RiggingJobHistoryEntry[];
  onSelectJob?: (job: RiggingJobHistoryEntry) => void;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("de-DE", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export function RiggingJobHistory({
  jobs,
  onSelectJob,
}: RiggingJobHistoryProps) {
  if (jobs.length === 0) {
    return (
      <div className="job-history">
        <h3>Rigging-Verlauf</h3>
        <p className="job-history__empty">
          Noch keine Rigging-Jobs in dieser Session.
        </p>
      </div>
    );
  }

  return (
    <div className="job-history">
      <h3>Rigging-Verlauf</h3>
      <ul className="job-history__list">
        {jobs.map((job) => (
          <li key={job.job_id} className="job-history__item">
            <button
              type="button"
              className="job-history__item-btn"
              onClick={() => onSelectJob?.(job)}
            >
              <div className="job-history__thumb job-history__thumb--mesh">
                <div className="job-history__placeholder" title="Source-Mesh">
                  🦴
                </div>
              </div>
              <div className="job-history__meta">
                <p className="job-history__model">{job.provider_key}</p>
                <span
                  className={`job-history__status job-history__status--${job.status}`}
                >
                  {job.status}
                </span>
                {job.created_at && (
                  <span className="job-history__created">
                    {formatDate(job.created_at)}
                  </span>
                )}
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

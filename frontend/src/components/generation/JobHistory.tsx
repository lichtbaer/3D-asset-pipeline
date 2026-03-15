import { Link } from "react-router-dom";

export interface JobHistoryEntry {
  job_id: string;
  prompt: string;
  model_key: string;
  status: string;
  result_url: string | null;
  asset_id?: string | null;
}

export interface JobHistoryProps {
  jobs: JobHistoryEntry[];
  /** resultUrl, assetId (für Asset-Verknüpfung beim nächsten Step) */
  onUseForMesh?: (resultUrl: string, assetId?: string) => void;
  onUseForBgRemoval?: (resultUrl: string, assetId?: string) => void;
}

function truncatePrompt(prompt: string, maxLen = 50): string {
  if (prompt.length <= maxLen) return prompt;
  return `${prompt.slice(0, maxLen)}…`;
}

export function JobHistory({
  jobs,
  onUseForMesh,
  onUseForBgRemoval,
}: JobHistoryProps) {
  if (jobs.length === 0) {
    return (
      <div className="job-history">
        <h3>Verlauf</h3>
        <p className="job-history__empty">Noch keine Jobs in dieser Session.</p>
      </div>
    );
  }

  return (
    <div className="job-history">
      <h3>Verlauf</h3>
      <ul className="job-history__list">
        {jobs.map((job) => (
          <li key={job.job_id} className="job-history__item">
            <div className="job-history__thumb">
              {job.status === "done" && job.result_url ? (
                <img
                  src={job.result_url}
                  alt=""
                  width={64}
                  height={64}
                  className="job-history__thumbnail"
                />
              ) : (
                <div className="job-history__placeholder" />
              )}
            </div>
            <div className="job-history__meta">
              <p className="job-history__prompt">
                {truncatePrompt(job.prompt)}
              </p>
              <p className="job-history__model">{job.model_key}</p>
              <span
                className={`job-history__status job-history__status--${job.status}`}
              >
                {job.status}
              </span>
              {job.status === "done" && job.result_url && (
                <>
                  {onUseForMesh && (
                    <button
                      type="button"
                      className="btn btn--outline btn--sm"
                      onClick={() => onUseForMesh(job.result_url!, job.asset_id ?? undefined)}
                    >
                      → Als Mesh-Input verwenden
                    </button>
                  )}
                  {onUseForBgRemoval && (
                    <button
                      type="button"
                      className="btn btn--outline btn--sm"
                      onClick={() => onUseForBgRemoval(job.result_url!, job.asset_id ?? undefined)}
                    >
                      → Freistellen
                    </button>
                  )}
                  {job.asset_id && (
                    <Link
                      to={`/assets/${job.asset_id}`}
                      className="job-history__library-link"
                    >
                      → In Bibliothek ansehen
                    </Link>
                  )}
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

import { Link } from "react-router-dom";

export interface BgRemovalJobHistoryEntry {
  job_id: string;
  source_image_url: string;
  provider_key: string;
  status: string;
  result_url: string | null;
  asset_id?: string | null;
}

export interface BgRemovalJobHistoryProps {
  jobs: BgRemovalJobHistoryEntry[];
  onUseForMesh?: (resultUrl: string) => void;
}

export function BgRemovalJobHistory({
  jobs,
  onUseForMesh,
}: BgRemovalJobHistoryProps) {
  if (jobs.length === 0) {
    return (
      <div className="job-history">
        <h3>Freistellungs-Verlauf</h3>
        <p className="job-history__empty">
          Noch keine Freistellungs-Jobs in dieser Session.
        </p>
      </div>
    );
  }

  return (
    <div className="job-history">
      <h3>Freistellungs-Verlauf</h3>
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
              <p className="job-history__model">{job.provider_key}</p>
              <span
                className={`job-history__status job-history__status--${job.status}`}
              >
                {job.status}
              </span>
              {job.status === "done" && job.result_url && onUseForMesh && (
                <button
                  type="button"
                  className="job-history__use-mesh"
                  onClick={() => onUseForMesh(job.result_url!)}
                >
                  → Als Mesh-Input verwenden
                </button>
              )}
              {job.status === "done" && job.asset_id && (
                <Link
                  to={`/assets/${job.asset_id}`}
                  className="job-history__library-link"
                >
                  → In Bibliothek ansehen
                </Link>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

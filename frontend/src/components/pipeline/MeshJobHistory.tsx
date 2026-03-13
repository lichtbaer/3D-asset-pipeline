import { Link } from "react-router-dom";

export interface MeshJobHistoryEntry {
  job_id: string;
  source_image_url: string;
  provider_key: string;
  status: string;
  glb_url: string | null;
  asset_id?: string | null;
}

export interface MeshJobHistoryProps {
  jobs: MeshJobHistoryEntry[];
}

export function MeshJobHistory({ jobs }: MeshJobHistoryProps) {
  if (jobs.length === 0) {
    return (
      <div className="job-history">
        <h3>Mesh-Verlauf</h3>
        <p className="job-history__empty">
          Noch keine Mesh-Jobs in dieser Session.
        </p>
      </div>
    );
  }

  return (
    <div className="job-history">
      <h3>Mesh-Verlauf</h3>
      <ul className="job-history__list">
        {jobs.map((job) => (
          <li key={job.job_id} className="job-history__item">
            <div className="job-history__thumb">
              <img
                src={job.source_image_url}
                alt=""
                width={64}
                height={64}
                className="job-history__thumbnail"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            </div>
            <div className="job-history__meta">
              <p className="job-history__model">{job.provider_key}</p>
              <span
                className={`job-history__status job-history__status--${job.status}`}
              >
                {job.status}
              </span>
              {job.status === "done" && job.glb_url && (
                <a
                  href={job.glb_url}
                  download
                  className="job-history__download"
                >
                  GLB herunterladen
                </a>
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

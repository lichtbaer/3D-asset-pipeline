import { useState } from "react";
import { AnimationMeshViewer } from "../../viewer/AnimationMeshViewer.js";

export interface AnimationJobHistoryEntry {
  job_id: string;
  motion_prompt: string;
  provider_key: string;
  status: string;
  animated_glb_url: string | null;
  created_at?: string;
  asset_id?: string | null;
}

export interface AnimationJobHistoryProps {
  jobs: AnimationJobHistoryEntry[];
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

export function AnimationJobHistory({ jobs }: AnimationJobHistoryProps) {
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  if (jobs.length === 0) {
    return (
      <div className="job-history">
        <h3>Animation-Verlauf</h3>
        <p className="job-history__empty">
          Noch keine Animation-Jobs in dieser Session.
        </p>
      </div>
    );
  }

  return (
    <div className="job-history">
      <h3>Animation-Verlauf</h3>
      <ul className="job-history__list">
        {jobs.map((job) => {
          const isExpanded = expandedJobId === job.job_id;
          return (
            <li key={job.job_id} className="job-history__item">
              <div className="job-history__meta">
                <p className="job-history__model">
                  {job.motion_prompt} · {job.provider_key}
                </p>
                <span
                  className={`job-history__status job-history__status--${job.status}`}
                >
                  {job.status}
                </span>
                {job.created_at && (
                  <span className="job-history__date" title={job.created_at}>
                    {formatDate(job.created_at)}
                  </span>
                )}
                {job.status === "done" && job.animated_glb_url && (
                  <button
                    type="button"
                    className="btn btn--outline btn--sm"
                    onClick={() =>
                      setExpandedJobId(isExpanded ? null : job.job_id)
                    }
                  >
                    {isExpanded ? "Vorschau schließen" : "Vorschau"}
                  </button>
                )}
                {job.status === "done" && job.animated_glb_url && (
                  <a
                    href={job.animated_glb_url}
                    download
                    className="job-history__download"
                  >
                    Animation herunterladen
                  </a>
                )}
                {job.status === "done" && job.asset_id && (
                  <a
                    href={`/assets/${job.asset_id}`}
                    className="job-history__library-link"
                  >
                    → In Bibliothek ansehen
                  </a>
                )}
              </div>
              {isExpanded && job.animated_glb_url && (
                <div className="job-history__preview">
                  <AnimationMeshViewer
                    glbUrl={job.animated_glb_url}
                    height={350}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

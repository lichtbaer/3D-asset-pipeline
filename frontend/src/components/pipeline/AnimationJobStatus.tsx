import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  getAnimationJobStatus,
  type AnimationJob,
} from "../../api/animation.js";
import { JobErrorBlock } from "../generation/JobErrorBlock.js";
import { MeshViewer } from "../viewer/MeshViewer.js";

export interface AnimationJobStatusProps {
  jobId: string | null;
  onJobUpdate?: (job: AnimationJob) => void;
}

export function AnimationJobStatus({
  jobId,
  onJobUpdate,
}: AnimationJobStatusProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["animation-job", jobId],
    queryFn: () => getAnimationJobStatus(jobId!),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 2000;
    },
    enabled: !!jobId,
  });

  useEffect(() => {
    if (data) {
      onJobUpdate?.(data);
    }
  }, [data, onJobUpdate]);

  if (!jobId) {
    return null;
  }

  if (isLoading && !data) {
    return (
      <div className="job-status job-status--loading">
        <div className="spinner" aria-hidden />
        <p>Job wird gestartet...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="job-status job-status--error">
        <p>
          Fehler beim Laden des Job-Status:{" "}
          {error instanceof Error ? error.message : "Unbekannter Fehler"}
        </p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { status, animated_glb_url } = data;

  if (status === "done" && animated_glb_url) {
    const isGlb = animated_glb_url.toLowerCase().endsWith(".glb");
    return (
      <div className="job-status job-status--done">
        <p className="job-status__label">Fertig!</p>
        <div className="animation-job-status__preview">
          {isGlb ? (
            <MeshViewer glbUrl={animated_glb_url} height={300} />
          ) : (
            <p>
              <a href={animated_glb_url} download className="job-status__download">
                Animation herunterladen (FBX)
              </a>
            </p>
          )}
        </div>
        {data.asset_id && (
          <Link to="/assets" className="job-status__library-link">
            → In Bibliothek ansehen
          </Link>
        )}
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="job-status job-status--failed">
        <JobErrorBlock
          errorType={data.error_type}
          errorDetail={data.error_detail ?? data.error_msg}
          providerKey={data.provider_key}
          failedAt={data.failed_at}
        />
      </div>
    );
  }

  return (
    <div className="job-status job-status--processing">
      <div className="spinner" aria-hidden />
      <p>
        {status === "pending"
          ? "Wartet auf Verarbeitung..."
          : "Animation wird generiert..."}
      </p>
    </div>
  );
}

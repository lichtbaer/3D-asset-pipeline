import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getRiggingJobStatus, type RiggingJob } from "../../api/rigging.js";
import { JobErrorBlock } from "../generation/JobErrorBlock.js";
import { MeshViewer } from "../viewer/MeshViewer.js";

export interface RiggingJobStatusProps {
  jobId: string | null;
  onJobUpdate?: (job: RiggingJob) => void;
}

export function RiggingJobStatus({
  jobId,
  onJobUpdate,
}: RiggingJobStatusProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["rigging-job", jobId],
    queryFn: () => getRiggingJobStatus(jobId!),
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

  const { status, glb_url } = data;

  if (status === "done" && glb_url) {
    return (
      <div className="job-status job-status--done">
        <p className="job-status__label">Rigging fertig!</p>
        <MeshViewer glbUrl={glb_url} height={350} />
        {data.asset_id && (
          <Link
            to={`/assets/${data.asset_id}`}
            className="job-status__library-link"
          >
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
          : "Wird geriggt..."}
      </p>
    </div>
  );
}

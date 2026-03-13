import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAnimationJobStatus,
  retryAnimationJob,
  type AnimationJob,
} from "../../../api/animation.js";
import { JobErrorBlock } from "../../generation/JobErrorBlock.js";
import { AnimationMeshViewer } from "../../viewer/AnimationMeshViewer.js";

export interface AnimationJobStatusProps {
  jobId: string | null;
  onJobUpdate?: (job: AnimationJob) => void;
  onRetrySuccess?: (newJobId: string) => void;
  onTryDifferentPreset?: () => void;
}

export function AnimationJobStatus({
  jobId,
  onJobUpdate,
  onRetrySuccess,
  onTryDifferentPreset,
}: AnimationJobStatusProps) {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["animation-job", jobId],
    queryFn: () => getAnimationJobStatus(jobId!),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 2000;
    },
    enabled: !!jobId,
  });

  const retryMutation = useMutation({
    mutationFn: () => retryAnimationJob(jobId!),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["animation-job", jobId] });
      onRetrySuccess?.(res.job_id);
    },
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
            <AnimationMeshViewer glbUrl={animated_glb_url} height={400} />
          ) : (
            <p>
              <a href={animated_glb_url} download className="job-status__download">
                Animation herunterladen (FBX)
              </a>
            </p>
          )}
        </div>
        <div className="compare-results__actions">
          <a href={animated_glb_url} download className="job-status__download">
            Download
          </a>
          {onTryDifferentPreset && (
            <button
              type="button"
              className="btn btn--outline btn--sm"
              onClick={onTryDifferentPreset}
            >
              → Nochmal mit anderem Preset
            </button>
          )}
          {data.asset_id && (
            <Link
              to={`/assets/${data.asset_id}`}
              className="job-history__library-link"
            >
              → In Bibliothek ansehen
            </Link>
          )}
        </div>
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
          onRetry={onRetrySuccess ? () => retryMutation.mutate() : undefined}
          isRetrying={retryMutation.isPending}
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
          : "HY-Motion generiert Animation..."}
      </p>
      <p className="animation-job-status__hint">
        Animation kann 60–120 Sekunden dauern
      </p>
    </div>
  );
}

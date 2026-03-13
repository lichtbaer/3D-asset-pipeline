import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getRiggingJob,
  retryRiggingJob,
  type RiggingJob,
} from "../../../api/rigging.js";
import { JobErrorBlock } from "../../generation/JobErrorBlock.js";
import { MeshViewer } from "../../viewer/MeshViewer.js";
import { usePipelineStore } from "../../../store/PipelineStore.js";

export interface RiggingJobStatusProps {
  jobId: string | null;
  onJobUpdate?: (job: RiggingJob) => void;
  onRetrySuccess?: (newJobId: string) => void;
}

export function RiggingJobStatus({
  jobId,
  onJobUpdate,
  onRetrySuccess,
}: RiggingJobStatusProps) {
  const queryClient = useQueryClient();
  const [, setSearchParams] = useSearchParams();
  const { setPendingAnimationGlbUrl } = usePipelineStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["rigging-job", jobId],
    queryFn: () => getRiggingJob(jobId!),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 2000;
    },
    enabled: !!jobId,
  });

  const retryMutation = useMutation({
    mutationFn: () => retryRiggingJob(jobId!),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["rigging-job", jobId] });
      onRetrySuccess?.(res.job_id);
    },
  });

  useEffect(() => {
    if (data) {
      onJobUpdate?.(data);
    }
  }, [data, onJobUpdate]);

  const handleUseForAnimation = () => {
    if (data?.result_url) {
      setPendingAnimationGlbUrl(data.result_url);
      setSearchParams({ tab: "animation" });
    }
  };

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

  const { status, result_url } = data;

  if (status === "done" && result_url) {
    return (
      <div className="job-status job-status--done">
        <p className="job-status__label">Fertig!</p>
        <MeshViewer glbUrl={result_url} height={400} />
        <div className="compare-results__actions">
          <button
            type="button"
            className="job-history__use-mesh"
            onClick={handleUseForAnimation}
          >
            → Animieren
          </button>
          <a
            href={result_url}
            download
            className="job-status__download"
          >
            Download GLB
          </a>
        </div>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="job-status job-status--failed">
        <JobErrorBlock
          errorType={data.error_type}
          errorDetail={data.error_detail}
          providerKey={data.provider_key}
          failedAt={undefined}
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
          : "UniRig analysiert Mesh..."}
      </p>
    </div>
  );
}

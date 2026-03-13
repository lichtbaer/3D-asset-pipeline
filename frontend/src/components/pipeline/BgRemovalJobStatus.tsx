import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getBgRemovalJobStatus,
  retryBgRemovalJob,
  type BgRemovalJob,
} from "../../api/bgremoval.js";
import { JobErrorBlock } from "../generation/JobErrorBlock.js";

export interface BgRemovalJobStatusProps {
  jobId: string | null;
  onJobUpdate?: (job: BgRemovalJob) => void;
  onUseForMesh?: (resultUrl: string) => void;
  onRetrySuccess?: (newJobId: string) => void;
}

export function BgRemovalJobStatus({
  jobId,
  onJobUpdate,
  onUseForMesh,
  onRetrySuccess,
}: BgRemovalJobStatusProps) {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["bgremoval-job", jobId],
    queryFn: () => getBgRemovalJobStatus(jobId!),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 2000;
    },
    enabled: !!jobId,
  });

  const retryMutation = useMutation({
    mutationFn: () => retryBgRemovalJob(jobId!),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["bgremoval-job", jobId] });
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

  const { status, result_url, source_image_url } = data;

  if (status === "done" && result_url) {
    return (
      <div className="job-status job-status--done">
        <p className="job-status__label">Fertig!</p>
        <div className="bgremoval-job-status__preview">
          <div className="bgremoval-job-status__preview-item">
            <span className="bgremoval-job-status__preview-label">Vorher</span>
            <img
              src={source_image_url}
              alt="Quellbild"
              className="job-status__image"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          </div>
          <div className="bgremoval-job-status__preview-item">
            <span className="bgremoval-job-status__preview-label">Nachher</span>
            <img
              src={result_url}
              alt="Freigestelltes Bild"
              className="job-status__image"
            />
          </div>
        </div>
        {onUseForMesh && (
          <button
            type="button"
            className="job-history__use-mesh"
            onClick={() => onUseForMesh(result_url)}
          >
            → Als Mesh-Input verwenden
          </button>
        )}
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
          : "Wird freigestellt..."}
      </p>
    </div>
  );
}

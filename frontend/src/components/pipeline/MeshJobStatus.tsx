import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getMeshJobStatus, retryMeshJob, type MeshJob } from "../../api/mesh.js";
import { JobErrorBlock } from "../generation/JobErrorBlock.js";
import { MeshViewer } from "../viewer/MeshViewer.js";
import { usePipelineStore } from "../../store/PipelineStore.js";

export interface MeshJobStatusProps {
  jobId: string | null;
  onJobUpdate?: (job: MeshJob) => void;
  onRetrySuccess?: (newJobId: string) => void;
}

export function MeshJobStatus({ jobId, onJobUpdate, onRetrySuccess }: MeshJobStatusProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [, setSearchParams] = useSearchParams();
  const { setPendingRiggingGlbUrl } = usePipelineStore();
  const { data, isLoading, error } = useQuery({
    queryKey: ["mesh-job", jobId],
    queryFn: () => getMeshJobStatus(jobId!),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 3000;
    },
    enabled: !!jobId,
  });

  const retryMutation = useMutation({
    mutationFn: () => retryMeshJob(jobId!),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["mesh-job", jobId] });
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

  const { status, glb_url } = data;

  const handleUseForRigging = () => {
    if (glb_url) {
      setPendingRiggingGlbUrl(glb_url);
      navigate("/pipeline");
      setSearchParams({ tab: "rigging" });
    }
  };

  if (status === "done" && glb_url) {
    return (
      <div className="job-status job-status--done">
        <p className="job-status__label">Fertig!</p>
        <MeshViewer glbUrl={glb_url} height={400} />
        <div className="compare-results__actions">
          <button
            type="button"
            className="job-history__use-mesh"
            onClick={handleUseForRigging}
          >
            → Riggen
          </button>
          {data.asset_id && (
            <Link
              to={`/assets/${data.asset_id}`}
              className="job-history__use-mesh"
            >
              → Als nächsten Schritt verwenden
            </Link>
          )}
          <a
            href={glb_url}
            download
            className="job-status__download"
          >
            Download GLB
          </a>
        </div>
        <p className="mesh-job-status__hint">
          Mesh-Generierung kann bis zu 5 Minuten dauern
        </p>
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
          : "Wird generiert..."}
      </p>
      <p className="mesh-job-status__hint">
        Mesh-Generierung kann bis zu 5 Minuten dauern
      </p>
    </div>
  );
}

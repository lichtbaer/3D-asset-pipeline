import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJobStatus, retryImageJob } from "../../api/generation.js";
import { getMeshJobStatus, retryMeshJob } from "../../api/mesh.js";
import { JobErrorBlock } from "../generation/JobErrorBlock.js";
import { TagSuggestionBanner } from "../assets/TagSuggestionBanner.js";
import { MeshViewer } from "../viewer/MeshViewer.js";

export type CompareStep = "image" | "mesh";

export interface CompareResultsProps {
  jobIdA: string | null;
  jobIdB: string | null;
  providerLabelA: string;
  providerLabelB: string;
  step: CompareStep;
  onUseForMesh?: (resultUrl: string) => void;
  onUseForBgRemoval?: (resultUrl: string) => void;
  onRetrySuccessA?: (newJobId: string) => void;
  onRetrySuccessB?: (newJobId: string) => void;
}

function CompareResultColumnImage({
  jobId,
  providerLabel,
  onUseForMesh,
  onUseForBgRemoval,
  onRetrySuccess,
}: {
  jobId: string;
  providerLabel: string;
  onUseForMesh?: (resultUrl: string) => void;
  onUseForBgRemoval?: (resultUrl: string) => void;
  onRetrySuccess?: (newJobId: string) => void;
}) {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJobStatus(jobId),
    refetchInterval: (query) => {
      const d = query.state.data as Awaited<ReturnType<typeof getJobStatus>> | undefined;
      const status = d?.status;
      return status === "done" || status === "failed" ? false : 2000;
    },
    enabled: !!jobId,
  });
  const retryMutation = useMutation({
    mutationFn: () => retryImageJob(jobId),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      onRetrySuccess?.(res.job_id);
    },
  });
  return (
    <CompareResultColumnContent
      data={data}
      isLoading={isLoading}
      error={error}
      providerLabel={providerLabel}
      step="image"
      onUseForMesh={onUseForMesh}
      onUseForBgRemoval={onUseForBgRemoval}
      onRetry={onRetrySuccess ? () => retryMutation.mutate() : undefined}
      isRetrying={retryMutation.isPending}
    />
  );
}

function CompareResultColumnMesh({
  jobId,
  providerLabel,
  onRetrySuccess,
}: {
  jobId: string;
  providerLabel: string;
  onRetrySuccess?: (newJobId: string) => void;
}) {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["mesh-job", jobId],
    queryFn: () => getMeshJobStatus(jobId),
    refetchInterval: (query) => {
      const d = query.state.data as Awaited<ReturnType<typeof getMeshJobStatus>> | undefined;
      const status = d?.status;
      return status === "done" || status === "failed" ? false : 3000;
    },
    enabled: !!jobId,
  });
  const retryMutation = useMutation({
    mutationFn: () => retryMeshJob(jobId),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["mesh-job", jobId] });
      onRetrySuccess?.(res.job_id);
    },
  });
  return (
    <CompareResultColumnContent
      data={data}
      isLoading={isLoading}
      error={error}
      providerLabel={providerLabel}
      step="mesh"
      onRetry={onRetrySuccess ? () => retryMutation.mutate() : undefined}
      isRetrying={retryMutation.isPending}
    />
  );
}

function CompareResultColumnContent({
  data,
  isLoading,
  error,
  providerLabel,
  step,
  onUseForMesh,
  onUseForBgRemoval,
  onRetry,
  isRetrying,
}: {
  data: Awaited<ReturnType<typeof getJobStatus>> | Awaited<ReturnType<typeof getMeshJobStatus>> | undefined;
  isLoading: boolean;
  error: Error | null;
  providerLabel: string;
  step: CompareStep;
  onUseForMesh?: (resultUrl: string) => void;
  onUseForBgRemoval?: (resultUrl: string) => void;
  onRetry?: () => void;
  isRetrying?: boolean;
}) {
  const isImage = step === "image";

  if (isLoading && !data) {
    return (
      <div className="compare-results__column">
        <h4 className="compare-results__column-title">{providerLabel}</h4>
        <div className="job-status job-status--loading">
          <div className="spinner" aria-hidden />
          <p>Job wird gestartet...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="compare-results__column">
        <h4 className="compare-results__column-title">{providerLabel}</h4>
        <div className="job-status job-status--error">
          <p>
            Fehler:{" "}
            {error instanceof Error ? error.message : "Unbekannter Fehler"}
          </p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const status = "status" in data ? data.status : "pending";

  if (isImage) {
    const imageJobData = data as Awaited<ReturnType<typeof getJobStatus>>;
    if (status === "done" && imageJobData.result_url) {
      return (
        <div className="compare-results__column">
          <h4 className="compare-results__column-title">{providerLabel}</h4>
          <div className="job-status job-status--done">
            <p className="job-status__label">Fertig!</p>
            <img
              src={imageJobData.result_url}
              alt="Generiertes Bild"
              className="job-status__image"
            />
            <div className="compare-results__actions">
              {onUseForMesh && (
                <button
                  type="button"
                  className="btn btn--outline btn--sm"
                  onClick={() => onUseForMesh(imageJobData.result_url!)}
                >
                  → Weiter verwenden (Mesh)
                </button>
              )}
              {onUseForBgRemoval && (
                <button
                  type="button"
                  className="btn btn--outline btn--sm"
                  onClick={() => onUseForBgRemoval(imageJobData.result_url!)}
                >
                  → Weiter verwenden (Freistellung)
                </button>
              )}
            </div>
          </div>
        </div>
      );
    }
    if (status === "failed") {
      return (
        <div className="compare-results__column">
          <h4 className="compare-results__column-title">{providerLabel}</h4>
          <div className="job-status job-status--failed">
            <JobErrorBlock
              errorType={imageJobData.error_type}
              errorDetail={imageJobData.error_detail ?? imageJobData.error_msg}
              providerKey={imageJobData.provider_key ?? imageJobData.model_key}
              failedAt={imageJobData.failed_at}
              onRetry={onRetry}
              isRetrying={isRetrying}
            />
          </div>
        </div>
      );
    }
    return (
      <div className="compare-results__column">
        <h4 className="compare-results__column-title">{providerLabel}</h4>
        <div className="job-status job-status--processing">
          <div className="spinner" aria-hidden />
          <p>
            {status === "pending"
              ? "Wartet auf Verarbeitung..."
              : "Wird generiert..."}
          </p>
        </div>
      </div>
    );
  }

  // Mesh
  const meshData = data as Awaited<ReturnType<typeof getMeshJobStatus>>;
  if (status === "done" && meshData.glb_url) {
    return (
      <div className="compare-results__column">
        <h4 className="compare-results__column-title">{providerLabel}</h4>
        <div className="job-status job-status--done">
          <p className="job-status__label">Fertig!</p>
          <MeshViewer glbUrl={meshData.glb_url} height={350} />
          <a
            href={meshData.glb_url}
            download
            className="job-status__download"
          >
            GLB herunterladen
          </a>
          {meshData.asset_id && (
            <TagSuggestionBanner
              assetId={meshData.asset_id}
              includeImageAnalysis={true}
            />
          )}
          <p className="mesh-job-status__hint">
            Mesh-Generierung kann bis zu 5 Minuten dauern
          </p>
        </div>
      </div>
    );
  }
  if (status === "failed") {
    return (
      <div className="compare-results__column">
        <h4 className="compare-results__column-title">{providerLabel}</h4>
        <div className="job-status job-status--failed">
          <JobErrorBlock
            errorType={meshData.error_type}
            errorDetail={meshData.error_detail ?? meshData.error_msg}
            providerKey={meshData.provider_key}
            failedAt={meshData.failed_at}
            onRetry={onRetry}
            isRetrying={isRetrying}
          />
        </div>
      </div>
    );
  }
  return (
    <div className="compare-results__column">
      <h4 className="compare-results__column-title">{providerLabel}</h4>
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
    </div>
  );
}

export function CompareResults({
  jobIdA,
  jobIdB,
  providerLabelA,
  providerLabelB,
  step,
  onUseForMesh,
  onUseForBgRemoval,
  onRetrySuccessA,
  onRetrySuccessB,
}: CompareResultsProps) {
  if (!jobIdA && !jobIdB) {
    return null;
  }

  return (
    <div className="compare-results">
      <h3>Vergleichsergebnis</h3>
      <div className="compare-results__grid">
        {jobIdA &&
          (step === "image" ? (
            <CompareResultColumnImage
              jobId={jobIdA}
              providerLabel={providerLabelA}
              onUseForMesh={onUseForMesh}
              onUseForBgRemoval={onUseForBgRemoval}
              onRetrySuccess={onRetrySuccessA}
            />
          ) : (
            <CompareResultColumnMesh
              jobId={jobIdA}
              providerLabel={providerLabelA}
              onRetrySuccess={onRetrySuccessA}
            />
          ))}
        {jobIdB &&
          (step === "image" ? (
            <CompareResultColumnImage
              jobId={jobIdB}
              providerLabel={providerLabelB}
              onUseForMesh={onUseForMesh}
              onUseForBgRemoval={onUseForBgRemoval}
              onRetrySuccess={onRetrySuccessB}
            />
          ) : (
            <CompareResultColumnMesh
              jobId={jobIdB}
              providerLabel={providerLabelB}
              onRetrySuccess={onRetrySuccessB}
            />
          ))}
      </div>
    </div>
  );
}

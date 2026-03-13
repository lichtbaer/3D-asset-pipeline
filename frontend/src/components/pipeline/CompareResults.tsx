import { useQuery } from "@tanstack/react-query";
import { getJobStatus } from "../../api/generation.js";
import { getMeshJobStatus } from "../../api/mesh.js";

export type CompareStep = "image" | "mesh";

export interface CompareResultsProps {
  jobIdA: string | null;
  jobIdB: string | null;
  providerLabelA: string;
  providerLabelB: string;
  step: CompareStep;
  onUseForMesh?: (resultUrl: string) => void;
  onUseForBgRemoval?: (resultUrl: string) => void;
}

function CompareResultColumnImage({
  jobId,
  providerLabel,
  onUseForMesh,
  onUseForBgRemoval,
}: {
  jobId: string;
  providerLabel: string;
  onUseForMesh?: (resultUrl: string) => void;
  onUseForBgRemoval?: (resultUrl: string) => void;
}) {
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
  return (
    <CompareResultColumnContent
      data={data}
      isLoading={isLoading}
      error={error}
      providerLabel={providerLabel}
      step="image"
      onUseForMesh={onUseForMesh}
      onUseForBgRemoval={onUseForBgRemoval}
    />
  );
}

function CompareResultColumnMesh({
  jobId,
  providerLabel,
}: {
  jobId: string;
  providerLabel: string;
}) {
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
  return (
    <CompareResultColumnContent
      data={data}
      isLoading={isLoading}
      error={error}
      providerLabel={providerLabel}
      step="mesh"
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
}: {
  data: Awaited<ReturnType<typeof getJobStatus>> | Awaited<ReturnType<typeof getMeshJobStatus>> | undefined;
  isLoading: boolean;
  error: Error | null;
  providerLabel: string;
  step: CompareStep;
  onUseForMesh?: (resultUrl: string) => void;
  onUseForBgRemoval?: (resultUrl: string) => void;
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
                  className="job-history__use-mesh"
                  onClick={() => onUseForMesh(imageJobData.result_url!)}
                >
                  → Weiter verwenden (Mesh)
                </button>
              )}
              {onUseForBgRemoval && (
                <button
                  type="button"
                  className="job-history__use-mesh"
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
            <p className="job-status__label">Fehlgeschlagen</p>
            <p className="job-status__error">
              {imageJobData.error_msg ?? "Unbekannter Fehler"}
            </p>
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
          <a
            href={meshData.glb_url}
            download
            className="job-status__download"
          >
            GLB herunterladen
          </a>
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
          <p className="job-status__label">Fehlgeschlagen</p>
          <p className="job-status__error">
            {meshData.error_msg ?? "Unbekannter Fehler"}
          </p>
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
            />
          ) : (
            <CompareResultColumnMesh
              jobId={jobIdA}
              providerLabel={providerLabelA}
            />
          ))}
        {jobIdB &&
          (step === "image" ? (
            <CompareResultColumnImage
              jobId={jobIdB}
              providerLabel={providerLabelB}
              onUseForMesh={onUseForMesh}
              onUseForBgRemoval={onUseForBgRemoval}
            />
          ) : (
            <CompareResultColumnMesh
              jobId={jobIdB}
              providerLabel={providerLabelB}
            />
          ))}
      </div>
    </div>
  );
}

import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getMeshJobStatus, type MeshJob } from "../../api/mesh.js";

export interface MeshJobStatusProps {
  jobId: string | null;
  onJobUpdate?: (job: MeshJob) => void;
}

export function MeshJobStatus({ jobId, onJobUpdate }: MeshJobStatusProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["mesh-job", jobId],
    queryFn: () => getMeshJobStatus(jobId!),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 3000;
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

  const { status, glb_url, error_msg } = data;

  if (status === "done" && glb_url) {
    return (
      <div className="job-status job-status--done">
        <p className="job-status__label">Fertig!</p>
        <a
          href={glb_url}
          download
          className="job-status__download"
        >
          GLB herunterladen
        </a>
        <p className="mesh-job-status__hint">
          Mesh-Generierung kann bis zu 5 Minuten dauern
        </p>
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
        <p className="job-status__label">Fehlgeschlagen</p>
        <p className="job-status__error">
          {error_msg ?? "Unbekannter Fehler bei der Generierung"}
        </p>
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

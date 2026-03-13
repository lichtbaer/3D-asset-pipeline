import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getJobStatus } from "../../api/generation.js";

export interface JobStatusProps {
  jobId: string | null;
  onJobUpdate?: (job: Awaited<ReturnType<typeof getJobStatus>>) => void;
}

export function JobStatus({ jobId, onJobUpdate }: JobStatusProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJobStatus(jobId!),
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

  const { status, result_url, error_msg } = data;

  if (status === "done" && result_url) {
    return (
      <div className="job-status job-status--done">
        <p className="job-status__label">Fertig!</p>
        <img
          src={result_url}
          alt="Generiertes Bild"
          className="job-status__image"
        />
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
        {status === "pending" ? "Wartet auf Verarbeitung..." : "Wird generiert..."}
      </p>
    </div>
  );
}

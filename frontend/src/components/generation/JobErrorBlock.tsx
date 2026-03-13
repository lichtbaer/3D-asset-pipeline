import { useState } from "react";

const MAX_DETAIL_LENGTH = 200;

export interface JobErrorBlockProps {
  errorType: string | null;
  errorDetail: string | null;
  providerKey: string;
  failedAt?: string | null;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export function JobErrorBlock({
  errorType,
  errorDetail,
  providerKey,
  failedAt,
  onRetry,
  isRetrying = false,
}: JobErrorBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const displayDetail = errorDetail ?? errorType ?? "Unbekannter Fehler";
  const isTruncated = displayDetail.length > MAX_DETAIL_LENGTH;
  const truncatedDetail = isTruncated
    ? displayDetail.slice(0, MAX_DETAIL_LENGTH) + "…"
    : displayDetail;
  const showDetail = expanded ? displayDetail : truncatedDetail;

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString("de-DE", {
        dateStyle: "short",
        timeStyle: "medium",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="job-error-block">
      <p className="job-error-block__label">Fehlgeschlagen</p>
      {errorType && (
        <p className="job-error-block__type">
          <strong>{errorType}</strong>
        </p>
      )}
      <p className="job-error-block__detail">
        <code>{showDetail}</code>
        {isTruncated && (
          <button
            type="button"
            className="job-error-block__toggle"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Weniger" : "Mehr"}
          </button>
        )}
      </p>
      <p className="job-error-block__meta">
        Provider: {providerKey}
        {failedAt && (
          <>
            {" · "}
            {formatDate(failedAt)}
          </>
        )}
      </p>
      {onRetry && (
        <button
          type="button"
          className="btn btn--danger"
          onClick={onRetry}
          disabled={isRetrying}
        >
          {isRetrying ? "Wird gestartet…" : "Erneut versuchen"}
        </button>
      )}
    </div>
  );
}

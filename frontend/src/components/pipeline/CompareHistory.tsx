import { useQuery } from "@tanstack/react-query";
import { getJobStatus } from "../../api/generation.js";
import { getMeshJobStatus } from "../../api/mesh.js";
import type { CompareStep } from "./CompareResults.js";

export interface CompareHistoryEntry {
  id: string;
  step: CompareStep;
  label: string;
  provider_key_a: string;
  provider_key_b: string;
  job_id_a: string;
  job_id_b: string;
}

export interface CompareHistoryProps {
  entries: CompareHistoryEntry[];
}

function truncate(str: string, maxLen = 40): string {
  if (str.length <= maxLen) return str;
  return `${str.slice(0, maxLen)}…`;
}

function CompareHistoryThumbImage({ jobId }: { jobId: string }) {
  const { data } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJobStatus(jobId),
    refetchInterval: (query) => {
      const d = query.state.data as Awaited<ReturnType<typeof getJobStatus>> | undefined;
      return d?.status === "done" || d?.status === "failed" ? false : 5000;
    },
    enabled: !!jobId,
  });
  if (!data) return <div className="compare-history__thumb-placeholder" />;
  if (data.status === "done" && data.result_url) {
    return (
      <img
        src={data.result_url}
        alt=""
        width={48}
        height={48}
        className="compare-history__thumb"
      />
    );
  }
  return (
    <div className="compare-history__thumb-placeholder compare-history__thumb--loading">
      …
    </div>
  );
}

function CompareHistoryThumbMesh({ jobId }: { jobId: string }) {
  const { data } = useQuery({
    queryKey: ["mesh-job", jobId],
    queryFn: () => getMeshJobStatus(jobId),
    refetchInterval: (query) => {
      const d = query.state.data as Awaited<ReturnType<typeof getMeshJobStatus>> | undefined;
      return d?.status === "done" || d?.status === "failed" ? false : 5000;
    },
    enabled: !!jobId,
  });
  if (!data) return <div className="compare-history__thumb-placeholder" />;
  if (data.status === "done" && data.glb_url) {
    return (
      <div className="compare-history__thumb compare-history__thumb--mesh">
        GLB
      </div>
    );
  }
  return (
    <div className="compare-history__thumb-placeholder compare-history__thumb--loading">
      …
    </div>
  );
}

function CompareHistoryItemThumb({
  jobId,
  step,
}: {
  jobId: string;
  step: CompareStep;
}) {
  return step === "image" ? (
    <CompareHistoryThumbImage jobId={jobId} />
  ) : (
    <CompareHistoryThumbMesh jobId={jobId} />
  );
}

export function CompareHistory({ entries }: CompareHistoryProps) {
  if (entries.length === 0) {
    return (
      <div className="job-history">
        <h3>Vergleichs-Verlauf</h3>
        <p className="job-history__empty">
          Noch keine Vergleiche in dieser Session.
        </p>
      </div>
    );
  }

  return (
    <div className="job-history">
      <h3>Vergleichs-Verlauf</h3>
      <ul className="job-history__list compare-history__list">
        {entries.map((entry) => (
          <li key={entry.id} className="job-history__item compare-history__item">
            <div className="compare-history__thumbs">
              <CompareHistoryItemThumb jobId={entry.job_id_a} step={entry.step} />
              <span className="compare-history__vs">vs</span>
              <CompareHistoryItemThumb jobId={entry.job_id_b} step={entry.step} />
            </div>
            <div className="job-history__meta">
              <p className="job-history__prompt">{truncate(entry.label)}</p>
              <p className="job-history__model">
                {entry.provider_key_a} vs {entry.provider_key_b}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

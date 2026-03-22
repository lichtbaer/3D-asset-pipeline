import { useCallback, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  postGenerateImage,
  getAvailableModels,
  type GenerateImageRequest,
  type GenerationJob,
} from "../api/generation.js";
import { PromptForm } from "../components/generation/PromptForm.js";
import { JobStatus } from "../components/generation/JobStatus.js";
import {
  JobHistory,
  type JobHistoryEntry,
} from "../components/generation/JobHistory.js";
import "./ImageGenerationPage.css";

function jobToHistoryEntry(job: GenerationJob, prompt: string): JobHistoryEntry {
  return {
    job_id: job.job_id,
    prompt,
    provider_key: job.provider_key,
    status: job.status,
    result_url: job.result_url,
  };
}

export function ImageGenerationPage() {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobHistory, setJobHistory] = useState<JobHistoryEntry[]>([]);

  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ["models"],
    queryFn: getAvailableModels,
  });

  const models = modelsData?.models ?? [];

  const createMutation = useMutation({
    mutationFn: postGenerateImage,
    onSuccess: (res, variables) => {
      setCurrentJobId(res.job_id);
      setJobHistory((prev) => [
        {
          job_id: res.job_id,
          prompt: variables.prompt,
          provider_key: variables.provider_key,
          status: "pending",
          result_url: null,
        },
        ...prev,
      ]);
    },
  });

  const handleJobUpdate = useCallback((job: GenerationJob) => {
    setJobHistory((prev) =>
      prev.map((entry) =>
        entry.job_id === job.job_id
          ? jobToHistoryEntry(job, entry.prompt)
          : entry
      )
    );
  }, []);

  const handleRetrySuccess = useCallback((newJobId: string) => {
    setCurrentJobId(newJobId);
    setJobHistory((prev) => {
      const failedJob = prev.find((j) => j.job_id === currentJobId);
      const newEntry: JobHistoryEntry = {
        job_id: newJobId,
        prompt: failedJob?.prompt ?? "",
        provider_key: failedJob?.provider_key ?? "",
        status: "pending",
        result_url: null,
      };
      return [newEntry, ...prev];
    });
  }, [currentJobId]);

  const currentJob = jobHistory.find((j) => j.job_id === currentJobId);
  const isJobRunning =
    !!currentJobId &&
    currentJob?.status !== "done" &&
    currentJob?.status !== "failed";

  const handleSubmit = (req: GenerateImageRequest) => {
    createMutation.mutate(req);
  };

  return (
    <main className="image-generation-page">
      <h1>Bildgenerierung</h1>

      <section className="image-generation-page__form">
        <PromptForm
          models={models}
          modelsLoading={modelsLoading}
          onSubmit={handleSubmit}
          disabled={isJobRunning}
        />
      </section>

      <section className="image-generation-page__status">
        <JobStatus
          jobId={currentJobId}
          onJobUpdate={handleJobUpdate}
          onRetrySuccess={handleRetrySuccess}
        />
      </section>

      <section className="image-generation-page__history">
        <JobHistory jobs={jobHistory} />
      </section>
    </main>
  );
}

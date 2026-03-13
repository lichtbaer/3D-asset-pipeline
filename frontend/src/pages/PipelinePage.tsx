import { useCallback, useState, useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  postGenerateImage,
  getAvailableModels,
  type GenerateImageRequest,
  type GenerationJob,
} from "../api/generation.js";
import {
  postGenerateMesh,
  getMeshProviders,
  type MeshJob,
} from "../api/mesh.js";
import {
  postBgRemoval,
  getBgRemovalProviders,
  type BgRemovalJob,
} from "../api/bgremoval.js";
import {
  getImageProviders,
  type ImageProvider,
} from "../api/generation.js";
import {
  startImageCompare,
  startMeshCompare,
  type CompareImageRequest,
  type CompareMeshRequest,
} from "../api/compare.js";
import { PromptForm } from "../components/generation/PromptForm.js";
import { JobStatus } from "../components/generation/JobStatus.js";
import {
  JobHistory,
  type JobHistoryEntry,
} from "../components/generation/JobHistory.js";
import { MeshForm } from "../components/pipeline/MeshForm.js";
import { MeshJobStatus } from "../components/pipeline/MeshJobStatus.js";
import {
  MeshJobHistory,
  type MeshJobHistoryEntry,
} from "../components/pipeline/MeshJobHistory.js";
import { BgRemovalForm } from "../components/pipeline/BgRemovalForm.js";
import { BgRemovalJobStatus } from "../components/pipeline/BgRemovalJobStatus.js";
import {
  BgRemovalJobHistory,
  type BgRemovalJobHistoryEntry,
} from "../components/pipeline/BgRemovalJobHistory.js";
import {
  CompareForm,
  type CompareStep,
} from "../components/pipeline/CompareForm.js";
import { CompareResults } from "../components/pipeline/CompareResults.js";
import {
  CompareHistory,
  type CompareHistoryEntry,
} from "../components/pipeline/CompareHistory.js";
import "./ImageGenerationPage.css";
import "./PipelinePage.css";

type TabId = "image" | "bgremoval" | "mesh" | "compare";

function jobToHistoryEntry(job: GenerationJob, prompt: string): JobHistoryEntry {
  return {
    job_id: job.job_id,
    prompt,
    model_key: job.model_key,
    status: job.status,
    result_url: job.result_url,
    asset_id: job.asset_id,
  };
}

function meshJobToHistoryEntry(job: MeshJob): MeshJobHistoryEntry {
  return {
    job_id: job.job_id,
    source_image_url: job.source_image_url,
    provider_key: job.provider_key,
    status: job.status,
    glb_url: job.glb_url,
    asset_id: job.asset_id,
  };
}

export function PipelinePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: TabId =
    tabParam === "compare"
      ? "compare"
      : tabParam === "mesh"
        ? "mesh"
        : tabParam === "bgremoval"
          ? "bgremoval"
          : "image";

  const [pendingMeshImageUrl, setPendingMeshImageUrl] = useState<string | null>(
    null
  );
  const [pendingBgRemovalImageUrl, setPendingBgRemovalImageUrl] = useState<
    string | null
  >(null);
  const [meshSourceImageUrl, setMeshSourceImageUrl] = useState("");
  const [bgRemovalSourceImageUrl, setBgRemovalSourceImageUrl] = useState("");

  const setActiveTab = useCallback(
    (tab: TabId) => {
      setSearchParams({ tab });
    },
    [setSearchParams]
  );

  useEffect(() => {
    if (pendingMeshImageUrl && activeTab === "mesh") {
      setMeshSourceImageUrl(pendingMeshImageUrl);
      setPendingMeshImageUrl(null);
    }
  }, [pendingMeshImageUrl, activeTab]);

  useEffect(() => {
    if (pendingBgRemovalImageUrl && activeTab === "bgremoval") {
      setBgRemovalSourceImageUrl(pendingBgRemovalImageUrl);
      setPendingBgRemovalImageUrl(null);
    }
  }, [pendingBgRemovalImageUrl, activeTab]);

  // URL-Parameter: ?tab=mesh&source=URL oder ?tab=bgremoval&source=URL (z.B. aus Asset-Bibliothek)
  useEffect(() => {
    const source = searchParams.get("source");
    const tab = searchParams.get("tab");
    if (source && tab === "mesh") {
      setMeshSourceImageUrl(source);
      setActiveTab("mesh");
    } else if (source && tab === "bgremoval") {
      setBgRemovalSourceImageUrl(source);
      setActiveTab("bgremoval");
    }
  }, [searchParams]);

  const handleUseForMesh = useCallback(
    (resultUrl: string) => {
      setPendingMeshImageUrl(resultUrl);
      setActiveTab("mesh");
    },
    [setActiveTab]
  );

  const handleUseForBgRemoval = useCallback(
    (resultUrl: string) => {
      setPendingBgRemovalImageUrl(resultUrl);
      setActiveTab("bgremoval");
    },
    [setActiveTab]
  );

  const handleCompareUseForMesh = useCallback(
    (resultUrl: string) => {
      setMeshSourceImageUrl(resultUrl);
      setActiveTab("mesh");
    },
    [setActiveTab]
  );

  const handleCompareUseForBgRemoval = useCallback(
    (resultUrl: string) => {
      setPendingBgRemovalImageUrl(resultUrl);
      setActiveTab("bgremoval");
    },
    [setActiveTab]
  );

  const [currentImageJobId, setCurrentImageJobId] = useState<string | null>(null);
  const [imageJobHistory, setImageJobHistory] = useState<JobHistoryEntry[]>([]);

  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ["models"],
    queryFn: getAvailableModels,
  });
  const models = modelsData?.models ?? [];

  const imageCreateMutation = useMutation({
    mutationFn: postGenerateImage,
    onSuccess: (res, variables) => {
      setCurrentImageJobId(res.job_id);
      setImageJobHistory((prev) => [
        {
          job_id: res.job_id,
          prompt: variables.prompt,
          model_key: variables.model_key,
          status: "pending",
          result_url: null,
        },
        ...prev,
      ]);
    },
  });

  const handleImageJobUpdate = useCallback((job: GenerationJob) => {
    setImageJobHistory((prev) =>
      prev.map((entry) =>
        entry.job_id === job.job_id
          ? jobToHistoryEntry(job, entry.prompt)
          : entry
      )
    );
  }, []);

  const currentImageJob = imageJobHistory.find(
    (j) => j.job_id === currentImageJobId
  );
  const isImageJobRunning =
    !!currentImageJobId &&
    currentImageJob?.status !== "done" &&
    currentImageJob?.status !== "failed";

  const [currentMeshJobId, setCurrentMeshJobId] = useState<string | null>(null);
  const [meshJobHistory, setMeshJobHistory] = useState<MeshJobHistoryEntry[]>(
    []
  );

  const { data: meshProvidersData, isLoading: meshProvidersLoading } =
    useQuery({
      queryKey: ["mesh-providers"],
      queryFn: getMeshProviders,
    });
  const meshProviders = useMemo(
    () => meshProvidersData?.providers ?? [],
    [meshProvidersData?.providers]
  );

  const meshCreateMutation = useMutation({
    mutationFn: postGenerateMesh,
    onSuccess: (res, variables) => {
      setCurrentMeshJobId(res.job_id);
      setMeshJobHistory((prev) => [
        {
          job_id: res.job_id,
          source_image_url: variables.source_image_url,
          provider_key: variables.provider_key,
          status: "pending",
          glb_url: null,
        },
        ...prev,
      ]);
    },
  });

  const handleMeshJobUpdate = useCallback((job: MeshJob) => {
    setMeshJobHistory((prev) =>
      prev.map((entry) =>
        entry.job_id === job.job_id ? meshJobToHistoryEntry(job) : entry
      )
    );
  }, []);

  const currentMeshJob = meshJobHistory.find(
    (j) => j.job_id === currentMeshJobId
  );
  const isMeshJobRunning =
    !!currentMeshJobId &&
    currentMeshJob?.status !== "done" &&
    currentMeshJob?.status !== "failed";

  const [currentBgRemovalJobId, setCurrentBgRemovalJobId] = useState<
    string | null
  >(null);
  const [bgRemovalJobHistory, setBgRemovalJobHistory] = useState<
    BgRemovalJobHistoryEntry[]
  >([]);

  const { data: bgRemovalProvidersData, isLoading: bgRemovalProvidersLoading } =
    useQuery({
      queryKey: ["bgremoval-providers"],
      queryFn: getBgRemovalProviders,
    });
  const bgRemovalProviders = bgRemovalProvidersData?.providers ?? [];

  const bgRemovalCreateMutation = useMutation({
    mutationFn: postBgRemoval,
    onSuccess: (res, variables) => {
      setCurrentBgRemovalJobId(res.job_id);
      setBgRemovalJobHistory((prev) => [
        {
          job_id: res.job_id,
          source_image_url: variables.source_image_url,
          provider_key: variables.provider_key,
          status: "pending",
          result_url: null,
        },
        ...prev,
      ]);
    },
  });

  const handleBgRemovalJobUpdate = useCallback((job: BgRemovalJob) => {
    setBgRemovalJobHistory((prev) =>
      prev.map((entry) =>
        entry.job_id === job.job_id
          ? {
              ...entry,
              status: job.status,
              result_url: job.result_url,
              asset_id: job.asset_id,
            }
          : entry
      )
    );
  }, []);

  const currentBgRemovalJob = bgRemovalJobHistory.find(
    (j) => j.job_id === currentBgRemovalJobId
  );
  const isBgRemovalJobRunning =
    !!currentBgRemovalJobId &&
    currentBgRemovalJob?.status !== "done" &&
    currentBgRemovalJob?.status !== "failed";

  const handleImageSubmit = (req: GenerateImageRequest) => {
    imageCreateMutation.mutate(req);
  };

  const handleMeshSubmit = (req: {
    source_image_url: string;
    provider_key: string;
    params: Record<string, unknown>;
    auto_bgremoval?: boolean;
    bgremoval_provider_key?: string;
  }) => {
    meshCreateMutation.mutate(req);
  };

  const handleBgRemovalSubmit = (req: {
    source_image_url: string;
    provider_key: string;
  }) => {
    bgRemovalCreateMutation.mutate(req);
  };

  const { data: imageProvidersData, isLoading: imageProvidersLoading } =
    useQuery({
      queryKey: ["image-providers"],
      queryFn: getImageProviders,
    });
  const imageProviders = useMemo<ImageProvider[]>(
    () => imageProvidersData?.providers ?? [],
    [imageProvidersData?.providers]
  );

  const [compareStep, setCompareStep] = useState<CompareStep>("image");
  const [compareJobIdA, setCompareJobIdA] = useState<string | null>(null);
  const [compareJobIdB, setCompareJobIdB] = useState<string | null>(null);
  const [compareProviderLabelA, setCompareProviderLabelA] = useState("");
  const [compareProviderLabelB, setCompareProviderLabelB] = useState("");
  const [compareHistory, setCompareHistory] = useState<CompareHistoryEntry[]>(
    []
  );

  const handleCompareImageSubmit = useCallback(
    (req: CompareImageRequest) => {
      startImageCompare(req).then(([jobIdA, jobIdB]) => {
        const labelA =
          imageProviders.find((p) => p.key === req.provider_key_a)
            ?.display_name ?? req.provider_key_a;
        const labelB =
          imageProviders.find((p) => p.key === req.provider_key_b)
            ?.display_name ?? req.provider_key_b;
        setCompareJobIdA(jobIdA);
        setCompareJobIdB(jobIdB);
        setCompareProviderLabelA(labelA);
        setCompareProviderLabelB(labelB);
        setCompareHistory((prev) => [
          {
            id: `${jobIdA}-${jobIdB}`,
            step: "image",
            label: req.prompt,
            provider_key_a: req.provider_key_a,
            provider_key_b: req.provider_key_b,
            job_id_a: jobIdA,
            job_id_b: jobIdB,
          },
          ...prev,
        ]);
      });
    },
    [imageProviders]
  );

  const handleCompareMeshSubmit = useCallback(
    (req: CompareMeshRequest) => {
      startMeshCompare(req).then(([jobIdA, jobIdB]) => {
        const labelA =
          meshProviders.find((p) => p.key === req.provider_key_a)
            ?.display_name ?? req.provider_key_a;
        const labelB =
          meshProviders.find((p) => p.key === req.provider_key_b)
            ?.display_name ?? req.provider_key_b;
        setCompareJobIdA(jobIdA);
        setCompareJobIdB(jobIdB);
        setCompareProviderLabelA(labelA);
        setCompareProviderLabelB(labelB);
        setCompareHistory((prev) => [
          {
            id: `${jobIdA}-${jobIdB}`,
            step: "mesh",
            label: req.source_image_url,
            provider_key_a: req.provider_key_a,
            provider_key_b: req.provider_key_b,
            job_id_a: jobIdA,
            job_id_b: jobIdB,
          },
          ...prev,
        ]);
      });
    },
    [meshProviders]
  );

  return (
    <main className="pipeline-page">
      <nav className="pipeline-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "image"}
          className={`pipeline-tabs__tab ${activeTab === "image" ? "pipeline-tabs__tab--active" : ""}`}
          onClick={() => setActiveTab("image")}
        >
          Bildgenerierung
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "bgremoval"}
          className={`pipeline-tabs__tab ${activeTab === "bgremoval" ? "pipeline-tabs__tab--active" : ""}`}
          onClick={() => setActiveTab("bgremoval")}
        >
          Freistellung
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "mesh"}
          className={`pipeline-tabs__tab ${activeTab === "mesh" ? "pipeline-tabs__tab--active" : ""}`}
          onClick={() => setActiveTab("mesh")}
        >
          Mesh-Generierung
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "compare"}
          className={`pipeline-tabs__tab ${activeTab === "compare" ? "pipeline-tabs__tab--active" : ""}`}
          onClick={() => setActiveTab("compare")}
        >
          Vergleich
        </button>
      </nav>

      {activeTab === "image" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Bildgenerierung</h1>
          <section className="pipeline-page__form">
            <PromptForm
              models={models}
              modelsLoading={modelsLoading}
              onSubmit={handleImageSubmit}
              disabled={isImageJobRunning}
            />
          </section>
          <section className="pipeline-page__status">
            <JobStatus
              jobId={currentImageJobId}
              onJobUpdate={handleImageJobUpdate}
            />
          </section>
          <section className="pipeline-page__history">
            <JobHistory
              jobs={imageJobHistory}
              onUseForMesh={handleUseForMesh}
              onUseForBgRemoval={handleUseForBgRemoval}
            />
          </section>
        </div>
      )}

      {activeTab === "bgremoval" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Freistellung</h1>
          <section className="pipeline-page__form">
            <BgRemovalForm
              sourceImageUrl={bgRemovalSourceImageUrl}
              onSourceImageUrlChange={setBgRemovalSourceImageUrl}
              providers={bgRemovalProviders}
              providersLoading={bgRemovalProvidersLoading}
              onSubmit={handleBgRemovalSubmit}
              disabled={isBgRemovalJobRunning}
            />
          </section>
          <section className="pipeline-page__status">
            <BgRemovalJobStatus
              jobId={currentBgRemovalJobId}
              onJobUpdate={handleBgRemovalJobUpdate}
              onUseForMesh={handleUseForMesh}
            />
          </section>
          <section className="pipeline-page__history">
            <BgRemovalJobHistory
              jobs={bgRemovalJobHistory}
              onUseForMesh={handleUseForMesh}
            />
          </section>
        </div>
      )}

      {activeTab === "mesh" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Mesh-Generierung</h1>
          <section className="pipeline-page__form">
            <MeshForm
              sourceImageUrl={meshSourceImageUrl}
              onSourceImageUrlChange={setMeshSourceImageUrl}
              providers={meshProviders}
              providersLoading={meshProvidersLoading}
              bgRemovalProviders={bgRemovalProviders}
              bgRemovalProvidersLoading={bgRemovalProvidersLoading}
              onSubmit={handleMeshSubmit}
              disabled={isMeshJobRunning}
            />
          </section>
          <section className="pipeline-page__status">
            <MeshJobStatus
              jobId={currentMeshJobId}
              onJobUpdate={handleMeshJobUpdate}
            />
          </section>
          <section className="pipeline-page__history">
            <MeshJobHistory jobs={meshJobHistory} />
          </section>
        </div>
      )}

      {activeTab === "compare" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Vergleich</h1>
          <section className="pipeline-page__form">
            <CompareForm
              step={compareStep}
              onStepChange={setCompareStep}
              imageProviders={imageProviders}
              imageProvidersLoading={imageProvidersLoading}
              meshProviders={meshProviders}
              meshProvidersLoading={meshProvidersLoading}
              onImageSubmit={handleCompareImageSubmit}
              onMeshSubmit={handleCompareMeshSubmit}
              disabled={false}
            />
          </section>
          <section className="pipeline-page__status">
            <CompareResults
              jobIdA={compareJobIdA}
              jobIdB={compareJobIdB}
              providerLabelA={compareProviderLabelA}
              providerLabelB={compareProviderLabelB}
              step={compareStep}
              onUseForMesh={handleCompareUseForMesh}
              onUseForBgRemoval={handleCompareUseForBgRemoval}
            />
          </section>
          <section className="pipeline-page__history">
            <CompareHistory entries={compareHistory} />
          </section>
        </div>
      )}
    </main>
  );
}

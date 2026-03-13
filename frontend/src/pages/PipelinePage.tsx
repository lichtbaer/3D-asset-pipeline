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
  postRigging,
  getRiggingProviders,
  type RiggingJob,
} from "../api/rigging.js";
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
import { RiggingForm } from "../components/pipeline/RiggingForm.js";
import { RiggingJobStatus } from "../components/pipeline/RiggingJobStatus.js";
import { ImageCompareForm } from "../components/pipeline/ImageCompareForm.js";
import { MeshCompareForm } from "../components/pipeline/MeshCompareForm.js";
import { CompareResults } from "../components/pipeline/CompareResults.js";
import {
  CompareHistory,
  type CompareHistoryEntry,
} from "../components/pipeline/CompareHistory.js";
import { usePipelineStore } from "../store/PipelineStore.js";
import "./ImageGenerationPage.css";
import "./PipelinePage.css";

type TabId = "image" | "bgremoval" | "mesh" | "rigging";

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
  const { activeAssetId, setActiveAssetId } = usePipelineStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: TabId =
    tabParam === "mesh"
      ? "mesh"
      : tabParam === "bgremoval"
        ? "bgremoval"
        : tabParam === "rigging"
          ? "rigging"
          : "image";

  const [pendingMeshImageUrl, setPendingMeshImageUrl] = useState<string | null>(
    null
  );
  const [pendingBgRemovalImageUrl, setPendingBgRemovalImageUrl] = useState<
    string | null
  >(null);
  const [meshSourceImageUrl, setMeshSourceImageUrl] = useState("");
  const [bgRemovalSourceImageUrl, setBgRemovalSourceImageUrl] = useState("");
  const [riggingSourceGlbUrl, setRiggingSourceGlbUrl] = useState("");
  const [pendingRiggingGlbUrl, setPendingRiggingGlbUrl] = useState<string | null>(
    null
  );

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

  useEffect(() => {
    if (pendingRiggingGlbUrl && activeTab === "rigging") {
      setRiggingSourceGlbUrl(pendingRiggingGlbUrl);
      setPendingRiggingGlbUrl(null);
    }
  }, [pendingRiggingGlbUrl, activeTab]);

  // Redirect ?tab=compare → ?tab=image (Vergleichsmodus ist jetzt in den Tabs integriert)
  useEffect(() => {
    if (searchParams.get("tab") === "compare") {
      setSearchParams({ tab: "image" });
    }
  }, [searchParams, setSearchParams]);

  // URL-Parameter: ?tab=mesh&source=URL oder ?tab=bgremoval&source=URL oder ?tab=rigging&source=URL (z.B. aus Asset-Bibliothek)
  useEffect(() => {
    const source = searchParams.get("source");
    const tab = searchParams.get("tab");
    if (source && tab === "mesh") {
      setMeshSourceImageUrl(source);
      setActiveTab("mesh");
    } else if (source && tab === "bgremoval") {
      setBgRemovalSourceImageUrl(source);
      setActiveTab("bgremoval");
    } else if (source && tab === "rigging") {
      setRiggingSourceGlbUrl(source);
      setActiveTab("rigging");
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

  const handleImageRetrySuccess = useCallback((newJobId: string) => {
    setCurrentImageJobId(newJobId);
    const failedJob = imageJobHistory.find((j) => j.job_id === currentImageJobId);
    setImageJobHistory((prev) => [
      {
        job_id: newJobId,
        prompt: failedJob?.prompt ?? "",
        model_key: failedJob?.model_key ?? "",
        status: "pending",
        result_url: null,
      },
      ...prev,
    ]);
  }, [currentImageJobId, imageJobHistory]);

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

  const handleMeshRetrySuccess = useCallback((newJobId: string) => {
    setCurrentMeshJobId(newJobId);
    const failedJob = meshJobHistory.find((j) => j.job_id === currentMeshJobId);
    setMeshJobHistory((prev) => [
      {
        job_id: newJobId,
        source_image_url: failedJob?.source_image_url ?? "",
        provider_key: failedJob?.provider_key ?? "",
        status: "pending",
        glb_url: null,
      },
      ...prev,
    ]);
  }, [currentMeshJobId, meshJobHistory]);

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

  const handleBgRemovalRetrySuccess = useCallback((newJobId: string) => {
    setCurrentBgRemovalJobId(newJobId);
    const failedJob = bgRemovalJobHistory.find((j) => j.job_id === currentBgRemovalJobId);
    setBgRemovalJobHistory((prev) => [
      {
        job_id: newJobId,
        source_image_url: failedJob?.source_image_url ?? "",
        provider_key: failedJob?.provider_key ?? "",
        status: "pending",
        result_url: null,
      },
      ...prev,
    ]);
  }, [currentBgRemovalJobId, bgRemovalJobHistory]);

  const currentBgRemovalJob = bgRemovalJobHistory.find(
    (j) => j.job_id === currentBgRemovalJobId
  );
  const isBgRemovalJobRunning =
    !!currentBgRemovalJobId &&
    currentBgRemovalJob?.status !== "done" &&
    currentBgRemovalJob?.status !== "failed";

  const { data: riggingProvidersData, isLoading: riggingProvidersLoading } =
    useQuery({
      queryKey: ["rigging-providers"],
      queryFn: getRiggingProviders,
    });
  const riggingProviders = riggingProvidersData?.providers ?? [];

  const [currentRiggingJobId, setCurrentRiggingJobId] = useState<string | null>(
    null
  );
  const [currentRiggingJobStatus, setCurrentRiggingJobStatus] = useState<
    RiggingJob["status"] | null
  >(null);

  const riggingCreateMutation = useMutation({
    mutationFn: postRigging,
    onSuccess: (res) => {
      setCurrentRiggingJobId(res.job_id);
      setCurrentRiggingJobStatus("pending");
    },
  });

  const handleRiggingJobUpdate = useCallback((job: RiggingJob) => {
    setCurrentRiggingJobStatus(job.status);
  }, []);

  const handleRiggingSubmit = (req: {
    source_glb_url: string;
    provider_key: string;
    asset_id?: string | null;
  }) => {
    const payload: {
      source_glb_url: string;
      provider_key: string;
      asset_id?: string;
    } = {
      source_glb_url: req.source_glb_url,
      provider_key: req.provider_key,
    };
    if (activeAssetId) {
      payload.asset_id = activeAssetId;
      setActiveAssetId(null);
    } else if (req.asset_id) {
      payload.asset_id = req.asset_id;
    }
    riggingCreateMutation.mutate(payload);
  };

  const isRiggingJobRunning =
    !!currentRiggingJobId &&
    currentRiggingJobStatus !== "done" &&
    currentRiggingJobStatus !== "failed";

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
    const payload: {
      source_image_url: string;
      provider_key: string;
      params: Record<string, unknown>;
      auto_bgremoval?: boolean;
      bgremoval_provider_key?: string;
      asset_id?: string;
    } = { ...req };
    if (activeAssetId) {
      payload.asset_id = activeAssetId;
      setActiveAssetId(null);
    }
    meshCreateMutation.mutate(payload);
  };

  const handleBgRemovalSubmit = (req: {
    source_image_url: string;
    provider_key: string;
  }) => {
    const payload: {
      source_image_url: string;
      provider_key: string;
      asset_id?: string;
    } = { ...req };
    if (activeAssetId) {
      payload.asset_id = activeAssetId;
      setActiveAssetId(null);
    }
    bgRemovalCreateMutation.mutate(payload);
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

  const [imageMode, setImageMode] = useState<"single" | "compare">("single");
  const [meshMode, setMeshMode] = useState<"single" | "compare">("single");

  const [imageCompareJobIdA, setImageCompareJobIdA] = useState<string | null>(
    null
  );
  const [imageCompareJobIdB, setImageCompareJobIdB] = useState<string | null>(
    null
  );
  const [imageCompareProviderLabelA, setImageCompareProviderLabelA] =
    useState("");
  const [imageCompareProviderLabelB, setImageCompareProviderLabelB] =
    useState("");
  const [imageCompareHistory, setImageCompareHistory] = useState<
    CompareHistoryEntry[]
  >([]);

  const [meshCompareJobIdA, setMeshCompareJobIdA] = useState<string | null>(
    null
  );
  const [meshCompareJobIdB, setMeshCompareJobIdB] = useState<string | null>(
    null
  );
  const [meshCompareProviderLabelA, setMeshCompareProviderLabelA] =
    useState("");
  const [meshCompareProviderLabelB, setMeshCompareProviderLabelB] =
    useState("");
  const [meshCompareHistory, setMeshCompareHistory] = useState<
    CompareHistoryEntry[]
  >([]);

  const handleCompareImageSubmit = useCallback(
    (req: CompareImageRequest) => {
      startImageCompare(req).then(([jobIdA, jobIdB]) => {
        const labelA =
          imageProviders.find((p) => p.key === req.provider_key_a)
            ?.display_name ?? req.provider_key_a;
        const labelB =
          imageProviders.find((p) => p.key === req.provider_key_b)
            ?.display_name ?? req.provider_key_b;
        setImageCompareJobIdA(jobIdA);
        setImageCompareJobIdB(jobIdB);
        setImageCompareProviderLabelA(labelA);
        setImageCompareProviderLabelB(labelB);
        setImageCompareHistory((prev) => [
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
        setMeshCompareJobIdA(jobIdA);
        setMeshCompareJobIdB(jobIdB);
        setMeshCompareProviderLabelA(labelA);
        setMeshCompareProviderLabelB(labelB);
        setMeshCompareHistory((prev) => [
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
          aria-selected={activeTab === "rigging"}
          className={`pipeline-tabs__tab ${activeTab === "rigging" ? "pipeline-tabs__tab--active" : ""}`}
          onClick={() => setActiveTab("rigging")}
        >
          Rigging
        </button>
      </nav>

      {activeTab === "image" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Bildgenerierung</h1>
          <div className="pipeline-mode-toggle" role="group" aria-label="Modus">
            <button
              type="button"
              className={`pipeline-mode-toggle__btn ${imageMode === "single" ? "pipeline-mode-toggle__btn--active" : ""}`}
              onClick={() => setImageMode("single")}
            >
              Einzelgenerierung
            </button>
            <button
              type="button"
              className={`pipeline-mode-toggle__btn ${imageMode === "compare" ? "pipeline-mode-toggle__btn--active" : ""}`}
              onClick={() => setImageMode("compare")}
            >
              Vergleich
            </button>
          </div>
          <section className="pipeline-page__form">
            {imageMode === "single" ? (
              <PromptForm
                models={models}
                modelsLoading={modelsLoading}
                onSubmit={handleImageSubmit}
                disabled={isImageJobRunning}
              />
            ) : (
              <ImageCompareForm
                imageProviders={imageProviders}
                imageProvidersLoading={imageProvidersLoading}
                onSubmit={handleCompareImageSubmit}
                disabled={false}
              />
            )}
          </section>
          <section className="pipeline-page__status">
            {imageMode === "single" ? (
              <JobStatus
                jobId={currentImageJobId}
                onJobUpdate={handleImageJobUpdate}
                onRetrySuccess={handleImageRetrySuccess}
              />
            ) : (
              <CompareResults
                jobIdA={imageCompareJobIdA}
                jobIdB={imageCompareJobIdB}
                providerLabelA={imageCompareProviderLabelA}
                providerLabelB={imageCompareProviderLabelB}
                step="image"
                onUseForMesh={handleCompareUseForMesh}
                onUseForBgRemoval={handleCompareUseForBgRemoval}
                onRetrySuccessA={(id) => setImageCompareJobIdA(id)}
                onRetrySuccessB={(id) => setImageCompareJobIdB(id)}
              />
            )}
          </section>
          <section className="pipeline-page__history">
            {imageMode === "single" ? (
              <JobHistory
                jobs={imageJobHistory}
                onUseForMesh={handleUseForMesh}
                onUseForBgRemoval={handleUseForBgRemoval}
              />
            ) : (
              <CompareHistory entries={imageCompareHistory} />
            )}
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
              onRetrySuccess={handleBgRemovalRetrySuccess}
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

      {activeTab === "rigging" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Rigging</h1>
          <section className="pipeline-page__form">
            <RiggingForm
              sourceGlbUrl={riggingSourceGlbUrl}
              onSourceGlbUrlChange={setRiggingSourceGlbUrl}
              providers={riggingProviders}
              providersLoading={riggingProvidersLoading}
              onSubmit={handleRiggingSubmit}
              disabled={isRiggingJobRunning}
              assetId={activeAssetId}
            />
          </section>
          <section className="pipeline-page__status">
            <RiggingJobStatus
              jobId={currentRiggingJobId}
              onJobUpdate={handleRiggingJobUpdate}
            />
          </section>
        </div>
      )}

      {activeTab === "mesh" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Mesh-Generierung</h1>
          <div className="pipeline-mode-toggle" role="group" aria-label="Modus">
            <button
              type="button"
              className={`pipeline-mode-toggle__btn ${meshMode === "single" ? "pipeline-mode-toggle__btn--active" : ""}`}
              onClick={() => setMeshMode("single")}
            >
              Einzelgenerierung
            </button>
            <button
              type="button"
              className={`pipeline-mode-toggle__btn ${meshMode === "compare" ? "pipeline-mode-toggle__btn--active" : ""}`}
              onClick={() => setMeshMode("compare")}
            >
              Vergleich
            </button>
          </div>
          <section className="pipeline-page__form">
            {meshMode === "single" ? (
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
            ) : (
              <MeshCompareForm
                sourceImageUrl={meshSourceImageUrl}
                onSourceImageUrlChange={setMeshSourceImageUrl}
                meshProviders={meshProviders}
                meshProvidersLoading={meshProvidersLoading}
                onSubmit={handleCompareMeshSubmit}
                disabled={false}
              />
            )}
          </section>
          <section className="pipeline-page__status">
            {meshMode === "single" ? (
              <MeshJobStatus
                jobId={currentMeshJobId}
                onJobUpdate={handleMeshJobUpdate}
                onRetrySuccess={handleMeshRetrySuccess}
              />
            ) : (
              <CompareResults
                jobIdA={meshCompareJobIdA}
                jobIdB={meshCompareJobIdB}
                providerLabelA={meshCompareProviderLabelA}
                providerLabelB={meshCompareProviderLabelB}
                step="mesh"
                onRetrySuccessA={(id) => setMeshCompareJobIdA(id)}
                onRetrySuccessB={(id) => setMeshCompareJobIdB(id)}
              />
            )}
          </section>
          <section className="pipeline-page__history">
            {meshMode === "single" ? (
              <MeshJobHistory jobs={meshJobHistory} />
            ) : (
              <CompareHistory entries={meshCompareHistory} />
            )}
          </section>
        </div>
      )}
    </main>
  );
}

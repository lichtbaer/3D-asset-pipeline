import { useCallback, useState, useEffect, useMemo, useRef } from "react";
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
  postGenerateAnimation,
  getAnimationProviders,
  type AnimationJob,
} from "../api/animation.js";
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
import { RiggingForm } from "../components/pipeline/rigging/RiggingForm.js";
import { RiggingJobStatus } from "../components/pipeline/rigging/RiggingJobStatus.js";
import {
  RiggingJobHistory,
  type RiggingJobHistoryEntry,
} from "../components/pipeline/rigging/RiggingJobHistory.js";
import { ImageCompareForm } from "../components/pipeline/ImageCompareForm.js";
import { MeshCompareForm } from "../components/pipeline/MeshCompareForm.js";
import { CompareResults } from "../components/pipeline/CompareResults.js";
import {
  CompareHistory,
  type CompareHistoryEntry,
} from "../components/pipeline/CompareHistory.js";
import { AnimationForm } from "../components/pipeline/animation/AnimationForm.js";
import { AnimationJobStatus } from "../components/pipeline/animation/AnimationJobStatus.js";
import {
  AnimationJobHistory,
  type AnimationJobHistoryEntry,
} from "../components/pipeline/animation/AnimationJobHistory.js";
import { usePipelineStore } from "../store/PipelineStore.js";
import { useAssetFromUrl } from "../hooks/useAssetFromUrl.js";
import { getAssetFileUrl } from "../api/assets.js";
import { getSketchfabStatus } from "../api/sketchfab.js";
import { getMeshSources } from "../api/meshProcessing.js";
import {
  MeshProcessingPanel,
  ProcessingResultsList,
} from "../components/assets/MeshProcessingPanel.js";
import { AssetPickerModal } from "../components/assets/AssetPickerModal.js";
import { AssetUploadZone } from "../components/assets/AssetUploadZone.js";
import { SketchfabImportModal } from "../components/assets/SketchfabImportModal.js";
import { useToast } from "../components/ui/ToastContext.js";
import { PipelineStepper, type PipelineStep } from "../components/ui/PipelineStepper.js";
import "./ImageGenerationPage.css";
import "./PipelinePage.css";

type TabId =
  | "image"
  | "bgremoval"
  | "mesh"
  | "rigging"
  | "animation"
  | "mesh-processing";

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

function animationJobToHistoryEntry(
  job: AnimationJob
): AnimationJobHistoryEntry {
  return {
    job_id: job.job_id,
    motion_prompt: job.motion_prompt,
    provider_key: job.provider_key,
    status: job.status,
    animated_glb_url: job.animated_glb_url,
    created_at: job.created_at,
    asset_id: job.asset_id,
  };
}

export function PipelinePage() {
  const {
    activeAssetId,
    setActiveAssetId,
    pendingRiggingGlbUrl,
    setPendingRiggingGlbUrl,
    pendingAnimationGlbUrl,
    setPendingAnimationGlbUrl,
  } = usePipelineStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: TabId =
    tabParam === "mesh"
      ? "mesh"
      : tabParam === "bgremoval"
        ? "bgremoval"
        : tabParam === "rigging"
          ? "rigging"
          : tabParam === "animation"
            ? "animation"
            : tabParam === "mesh-processing"
              ? "mesh-processing"
              : "image";

  const [assetPickerOpen, setAssetPickerOpen] = useState<{
    tab: "rigging" | "animation" | "mesh-processing";
  } | null>(null);
  const [showSketchfabImport, setShowSketchfabImport] = useState(false);

  const [pendingMeshImageUrl, setPendingMeshImageUrl] = useState<string | null>(
    null
  );
  const [pendingBgRemovalImageUrl, setPendingBgRemovalImageUrl] = useState<
    string | null
  >(null);
  const [meshSourceImageUrl, setMeshSourceImageUrl] = useState("");
  const [bgRemovalSourceImageUrl, setBgRemovalSourceImageUrl] = useState("");
  const [riggingSourceGlbUrl, setRiggingSourceGlbUrl] = useState("");
  const [animationSourceGlbUrl, setAnimationSourceGlbUrl] = useState("");

  const setActiveTab = useCallback(
    (tab: TabId) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("tab", tab);
        const aid = prev.get("assetId");
        if (aid) next.set("assetId", aid);
        return next;
      });
    },
    [setSearchParams]
  );

  const { assetId: urlAssetId, asset: urlAsset } = useAssetFromUrl();
  const { addToast } = useToast();
  const prevJobStatuses = useRef(new Map<string, string>());

  const clearAssetFromUrl = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("assetId");
      return next;
    });
    if (activeTab === "rigging") setRiggingSourceGlbUrl("");
    if (activeTab === "animation") setAnimationSourceGlbUrl("");
  }, [setSearchParams, activeTab]);

  const handleAssetPickerSelect = useCallback(
    (
      asset: { asset_id: string; steps: Record<string, { file?: string }> },
      tab: "rigging" | "animation" | "mesh-processing"
    ) => {
      const aid = asset.asset_id;
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("tab", tab);
        next.set("assetId", aid);
        return next;
      });
      setAssetPickerOpen(null);
      if (tab === "rigging" && asset.steps.mesh?.file) {
        setRiggingSourceGlbUrl(getAssetFileUrl(aid, asset.steps.mesh.file));
      }
      if (tab === "animation" && asset.steps.rigging?.file) {
        setAnimationSourceGlbUrl(
          getAssetFileUrl(aid, asset.steps.rigging.file)
        );
      }
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
  }, [pendingRiggingGlbUrl, activeTab, setPendingRiggingGlbUrl]);

  useEffect(() => {
    if (pendingAnimationGlbUrl && activeTab === "animation") {
      setAnimationSourceGlbUrl(pendingAnimationGlbUrl);
      setPendingAnimationGlbUrl(null);
    }
  }, [pendingAnimationGlbUrl, activeTab, setPendingAnimationGlbUrl]);

  // Redirect ?tab=compare → ?tab=image (Vergleichsmodus ist jetzt in den Tabs integriert)
  useEffect(() => {
    if (searchParams.get("tab") === "compare") {
      setSearchParams({ tab: "image" });
    }
  }, [searchParams, setSearchParams]);

  // URL-Parameter: ?tab=X&source=URL oder ?tab=X&assetId=ID
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
    } else if (source && tab === "animation") {
      setAnimationSourceGlbUrl(source);
      setActiveTab("animation");
    }
  }, [searchParams]);

  // URL assetId: Asset laden und Source-URLs setzen
  useEffect(() => {
    if (!urlAsset || !urlAssetId) return;
    const tab = searchParams.get("tab");
    const steps = urlAsset.steps ?? {};

    if (tab === "rigging") {
      const mesh = steps.mesh;
      if (mesh && typeof mesh === "object" && "file" in mesh) {
        const file = String((mesh as { file: string }).file);
        setRiggingSourceGlbUrl(getAssetFileUrl(urlAssetId, file));
      }
    } else if (tab === "animation") {
      const rigging = steps.rigging;
      if (rigging && typeof rigging === "object" && "file" in rigging) {
        const file = String((rigging as { file: string }).file);
        setAnimationSourceGlbUrl(getAssetFileUrl(urlAssetId, file));
      }
    } else if (tab === "bgremoval") {
      const image = steps.image;
      if (image && typeof image === "object" && "file" in image) {
        const file = String((image as { file: string }).file);
        setBgRemovalSourceImageUrl(getAssetFileUrl(urlAssetId, file));
      }
    } else if (tab === "mesh") {
      const bgremoval = steps.bgremoval;
      const image = steps.image;
      const file = bgremoval && typeof bgremoval === "object" && "file" in bgremoval
        ? String((bgremoval as { file: string }).file)
        : image && typeof image === "object" && "file" in image
          ? String((image as { file: string }).file)
          : null;
      if (file) {
        setMeshSourceImageUrl(getAssetFileUrl(urlAssetId, file));
      }
    }
  }, [urlAsset, urlAssetId, searchParams]);

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
    const prevStatus = prevJobStatuses.current.get(job.job_id);
    if (prevStatus !== job.status) {
      prevJobStatuses.current.set(job.job_id, job.status);
      if (job.status === "done") addToast("Bildgenerierung abgeschlossen!", "success");
      if (job.status === "failed") addToast("Bildgenerierung fehlgeschlagen.", "error");
    }
  }, [addToast]);

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
    const prevStatus = prevJobStatuses.current.get(job.job_id);
    if (prevStatus !== job.status) {
      prevJobStatuses.current.set(job.job_id, job.status);
      if (job.status === "done") addToast("Mesh-Generierung abgeschlossen!", "success");
      if (job.status === "failed") addToast("Mesh-Generierung fehlgeschlagen.", "error");
    }
  }, [addToast]);

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
    const prevStatus = prevJobStatuses.current.get(job.job_id);
    if (prevStatus !== job.status) {
      prevJobStatuses.current.set(job.job_id, job.status);
      if (job.status === "done") addToast("Freistellung abgeschlossen!", "success");
      if (job.status === "failed") addToast("Freistellung fehlgeschlagen.", "error");
    }
  }, [addToast]);

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

  const [currentRiggingJobId, setCurrentRiggingJobId] = useState<string | null>(
    null
  );
  const [riggingJobHistory, setRiggingJobHistory] = useState<
    RiggingJobHistoryEntry[]
  >([]);

  const { data: riggingProvidersData, isLoading: riggingProvidersLoading } =
    useQuery({
      queryKey: ["rigging-providers"],
      queryFn: getRiggingProviders,
    });
  const riggingProviders = useMemo(
    () => riggingProvidersData?.providers ?? [],
    [riggingProvidersData?.providers]
  );

  const { data: riggingMeshSourcesData } = useQuery({
    queryKey: ["rigging-mesh-sources", activeAssetId],
    queryFn: () => getMeshSources(activeAssetId!),
    enabled: !!activeAssetId && activeTab === "rigging",
  });
  const riggingMeshFiles = useMemo(
    () => riggingMeshSourcesData?.sources ?? [],
    [riggingMeshSourcesData?.sources]
  );

  const riggingCreateMutation = useMutation({
    mutationFn: postRigging,
    onSuccess: (res, variables) => {
      setCurrentRiggingJobId(res.job_id);
      setRiggingJobHistory((prev) => [
        {
          job_id: res.job_id,
          source_glb_url: variables.source_glb_url,
          provider_key: variables.provider_key,
          status: "pending",
          glb_url: null,
          asset_id: variables.asset_id ?? null,
          created_at: new Date().toISOString(),
        },
        ...prev,
      ]);
    },
  });

  const handleRiggingJobUpdate = useCallback((job: RiggingJob) => {
    setRiggingJobHistory((prev) =>
      prev.map((entry) =>
        entry.job_id === job.job_id
          ? {
              ...entry,
              status: job.status,
              glb_url: job.glb_url,
              created_at: job.created_at,
            }
          : entry
      )
    );
    const prevStatus = prevJobStatuses.current.get(job.job_id);
    if (prevStatus !== job.status) {
      prevJobStatuses.current.set(job.job_id, job.status);
      if (job.status === "done") addToast("Rigging abgeschlossen!", "success");
      if (job.status === "failed") addToast("Rigging fehlgeschlagen.", "error");
    }
  }, [addToast]);

  const handleRiggingRetrySuccess = useCallback((newJobId: string) => {
    setCurrentRiggingJobId(newJobId);
    const failedJob = riggingJobHistory.find(
      (j) => j.job_id === currentRiggingJobId
    );
    setRiggingJobHistory((prev) => [
      {
        job_id: newJobId,
        source_glb_url: failedJob?.source_glb_url ?? "",
        provider_key: failedJob?.provider_key ?? "",
        status: "pending",
        glb_url: null,
        asset_id: failedJob?.asset_id ?? null,
        created_at: new Date().toISOString(),
      },
      ...prev,
    ]);
  }, [currentRiggingJobId, riggingJobHistory]);

  const handleRiggingSubmit = (req: {
    source_glb_url: string;
    provider_key: string;
    asset_id?: string | null;
  }) => {
    const payload: {
      source_glb_url: string;
      provider_key: string;
      asset_id?: string | null;
    } = { ...req };
    if (activeAssetId) {
      payload.asset_id = activeAssetId;
      setActiveAssetId(null);
    } else if (req.asset_id) {
      payload.asset_id = req.asset_id;
    }
    riggingCreateMutation.mutate(payload);
  };

  const handleRiggingJobSelect = useCallback((job: RiggingJobHistoryEntry) => {
    setCurrentRiggingJobId(job.job_id);
  }, []);

  const currentRiggingJob = riggingJobHistory.find(
    (j) => j.job_id === currentRiggingJobId
  );
  const isRiggingJobRunning =
    !!currentRiggingJobId &&
    currentRiggingJob?.status !== "done" &&
    currentRiggingJob?.status !== "failed";

  const [currentAnimationJobId, setCurrentAnimationJobId] = useState<
    string | null
  >(null);
  const [animationJobHistory, setAnimationJobHistory] = useState<
    AnimationJobHistoryEntry[]
  >([]);
  const { data: animationProvidersData, isLoading: animationProvidersLoading } =
    useQuery({
      queryKey: ["animation-providers"],
      queryFn: getAnimationProviders,
    });
  const animationProviders = useMemo(
    () => animationProvidersData?.providers ?? [],
    [animationProvidersData?.providers]
  );

  const animationCreateMutation = useMutation({
    mutationFn: postGenerateAnimation,
    onSuccess: (res, variables) => {
      setCurrentAnimationJobId(res.job_id);
      setAnimationJobHistory((prev) => [
        {
          job_id: res.job_id,
          motion_prompt: variables.motion_prompt,
          provider_key: variables.provider_key,
          status: "pending",
          animated_glb_url: null,
          created_at: new Date().toISOString(),
        },
        ...prev,
      ]);
    },
  });

  const handleAnimationJobUpdate = useCallback((job: AnimationJob) => {
    setAnimationJobHistory((prev) =>
      prev.map((entry) =>
        entry.job_id === job.job_id
          ? animationJobToHistoryEntry(job)
          : entry
      )
    );
    const prevStatus = prevJobStatuses.current.get(job.job_id);
    if (prevStatus !== job.status) {
      prevJobStatuses.current.set(job.job_id, job.status);
      if (job.status === "done") addToast("Animation abgeschlossen!", "success");
      if (job.status === "failed") addToast("Animation fehlgeschlagen.", "error");
    }
  }, [addToast]);

  const handleAnimationRetrySuccess = useCallback((newJobId: string) => {
    setCurrentAnimationJobId(newJobId);
    const failedJob = animationJobHistory.find(
      (j) => j.job_id === currentAnimationJobId
    );
    setAnimationJobHistory((prev) => [
      {
        job_id: newJobId,
        motion_prompt: failedJob?.motion_prompt ?? "",
        provider_key: failedJob?.provider_key ?? "",
        status: "pending",
        animated_glb_url: null,
        created_at: new Date().toISOString(),
      },
      ...prev,
    ]);
  }, [currentAnimationJobId, animationJobHistory]);

  const currentAnimationJob = animationJobHistory.find(
    (j) => j.job_id === currentAnimationJobId
  );
  const isAnimationJobRunning =
    !!currentAnimationJobId &&
    currentAnimationJob?.status !== "done" &&
    currentAnimationJob?.status !== "failed";

  const handleAnimationSubmit = (req: {
    source_glb_url: string;
    motion_prompt: string;
    provider_key: string;
    params?: Record<string, unknown>;
    asset_id?: string;
  }) => {
    const payload: {
      source_glb_url: string;
      motion_prompt: string;
      provider_key: string;
      params?: Record<string, unknown>;
      asset_id?: string;
    } = { ...req };
    if (activeAssetId) {
      payload.asset_id = activeAssetId;
      setActiveAssetId(null);
    }
    animationCreateMutation.mutate(payload);
  };

  const handleTryDifferentPreset = useCallback(() => {
    setCurrentAnimationJobId(null);
  }, []);

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

  const { data: sketchfabEnabled } = useQuery({
    queryKey: ["sketchfab-status"],
    queryFn: getSketchfabStatus,
  });

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

  const stepCompletion = {
    image: !!urlAsset?.steps?.image?.file,
    bgremoval: !!urlAsset?.steps?.bgremoval?.file,
    mesh: !!urlAsset?.steps?.mesh?.file,
    rigging: !!urlAsset?.steps?.rigging?.file,
    animation: !!urlAsset?.steps?.animation?.file,
  };

  const pipelineSteps: PipelineStep[] = [
    { id: "image", label: "Bild", completed: stepCompletion.image, active: activeTab === "image", disabled: false },
    { id: "bgremoval", label: "Freistellung", completed: stepCompletion.bgremoval, active: activeTab === "bgremoval", disabled: false },
    { id: "mesh", label: "Mesh", completed: stepCompletion.mesh, active: activeTab === "mesh" || activeTab === "mesh-processing", disabled: false,
      subSteps: [{ id: "mesh-processing", label: "Processing", completed: false, active: activeTab === "mesh-processing", disabled: !stepCompletion.mesh }]
    },
    { id: "rigging", label: "Rigging", completed: stepCompletion.rigging, active: activeTab === "rigging", disabled: false },
    { id: "animation", label: "Animation", completed: stepCompletion.animation, active: activeTab === "animation", disabled: false },
  ];

  return (
    <main className="pipeline-page">
      <PipelineStepper steps={pipelineSteps} onStepClick={(id) => setActiveTab(id as TabId)} />

      {activeTab === "image" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Bildgenerierung</h1>
          {sketchfabEnabled?.enabled && (
            <p className="pipeline-tab__sketchfab-link">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setShowSketchfabImport(true)}
              >
                Von Sketchfab importieren
              </button>
            </p>
          )}
          <div className="pipeline-mode-toggle" role="group" aria-label="Modus">
            <button
              type="button"
              className={`btn btn--ghost ${imageMode === "single" ? "pipeline-mode-toggle__btn--active" : ""}`}
              onClick={() => setImageMode("single")}
            >
              Einzelgenerierung
            </button>
            <button
              type="button"
              className={`btn btn--ghost ${imageMode === "compare" ? "pipeline-mode-toggle__btn--active" : ""}`}
              onClick={() => setImageMode("compare")}
            >
              Vergleich
            </button>
          </div>
          <section className="pipeline-page__form">
            <div className="pipeline-page__upload-row">
              <AssetUploadZone
                type="image"
                compact
                onSuccess={(assetId, file) => {
                  setSearchParams({ tab: "bgremoval", assetId });
                  setBgRemovalSourceImageUrl(
                    getAssetFileUrl(assetId, file ?? "image_original.png")
                  );
                }}
              />
              <span className="pipeline-page__upload-hint">
                oder Bild generieren:
              </span>
            </div>
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

      {activeTab === "mesh" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Mesh-Generierung</h1>
          <div className="pipeline-mode-toggle" role="group" aria-label="Modus">
            <button
              type="button"
              className={`btn btn--ghost ${meshMode === "single" ? "pipeline-mode-toggle__btn--active" : ""}`}
              onClick={() => setMeshMode("single")}
            >
              Einzelgenerierung
            </button>
            <button
              type="button"
              className={`btn btn--ghost ${meshMode === "compare" ? "pipeline-mode-toggle__btn--active" : ""}`}
              onClick={() => setMeshMode("compare")}
            >
              Vergleich
            </button>
          </div>
          <section className="pipeline-page__form">
            <div className="pipeline-page__upload-row">
              <AssetUploadZone
                type="mesh"
                compact
                onSuccess={(assetId, file) => {
                  setSearchParams({ tab: "rigging", assetId });
                  setRiggingSourceGlbUrl(
                    getAssetFileUrl(assetId, file ?? "mesh.glb")
                  );
                }}
              />
              <span className="pipeline-page__upload-hint">
                oder Mesh aus Bild generieren:
              </span>
            </div>
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

      {activeTab === "rigging" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Rigging</h1>
          <div className="pipeline-asset-context">
            {urlAssetId && urlAsset ? (
              <div className="pipeline-asset-context__loaded">
                <span>
                  Aktuell geladen: Asset {urlAssetId.slice(0, 8)}…
                </span>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={clearAssetFromUrl}
                >
                  ✕ Entfernen
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="btn btn--outline"
                onClick={() =>
                  setAssetPickerOpen({ tab: "rigging" })
                }
              >
                Aus Bibliothek laden
              </button>
            )}
          </div>
          <section className="pipeline-page__form">
            <RiggingForm
              sourceGlbUrl={riggingSourceGlbUrl}
              onSourceGlbUrlChange={setRiggingSourceGlbUrl}
              providers={riggingProviders}
              providersLoading={riggingProvidersLoading}
              onSubmit={handleRiggingSubmit}
              disabled={isRiggingJobRunning}
              assetId={activeAssetId}
              availableMeshFiles={riggingMeshFiles}
            />
          </section>
          <section className="pipeline-page__status">
            <RiggingJobStatus
              jobId={currentRiggingJobId}
              onJobUpdate={handleRiggingJobUpdate}
              onRetrySuccess={handleRiggingRetrySuccess}
            />
          </section>
          <section className="pipeline-page__history">
            <RiggingJobHistory
              jobs={riggingJobHistory}
              onSelectJob={handleRiggingJobSelect}
            />
          </section>
        </div>
      )}

      {activeTab === "animation" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Animation</h1>
          <div className="pipeline-asset-context">
            {urlAssetId && urlAsset ? (
              <div className="pipeline-asset-context__loaded">
                <span>
                  Aktuell geladen: Asset {urlAssetId.slice(0, 8)}…
                </span>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={clearAssetFromUrl}
                >
                  ✕ Entfernen
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="btn btn--outline"
                onClick={() =>
                  setAssetPickerOpen({ tab: "animation" })
                }
              >
                Aus Bibliothek laden
              </button>
            )}
          </div>
          <section className="pipeline-page__form">
            <AnimationForm
              sourceGlbUrl={animationSourceGlbUrl}
              onSourceGlbUrlChange={setAnimationSourceGlbUrl}
              providers={animationProviders}
              providersLoading={animationProvidersLoading}
              onSubmit={handleAnimationSubmit}
              disabled={isAnimationJobRunning}
            />
          </section>
          <section className="pipeline-page__status">
            <AnimationJobStatus
              jobId={currentAnimationJobId}
              onJobUpdate={handleAnimationJobUpdate}
              onRetrySuccess={handleAnimationRetrySuccess}
              onTryDifferentPreset={handleTryDifferentPreset}
            />
          </section>
          <section className="pipeline-page__history">
            <AnimationJobHistory jobs={animationJobHistory} />
          </section>
        </div>
      )}

      {activeTab === "mesh-processing" && (
        <div className="pipeline-tab-content" role="tabpanel">
          <h1>Mesh-Processing</h1>
          <div className="pipeline-asset-context">
            {urlAssetId && urlAsset ? (
              <div className="pipeline-asset-context__loaded">
                <span>
                  Aktuell geladen: Asset {urlAssetId.slice(0, 8)}…
                </span>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={clearAssetFromUrl}
                >
                  ✕ Entfernen
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="btn btn--outline"
                onClick={() =>
                  setAssetPickerOpen({ tab: "mesh-processing" })
                }
              >
                Aus Bibliothek laden
              </button>
            )}
          </div>
          {urlAssetId ? (
            <>
              <MeshProcessingPanel assetId={urlAssetId} />
              {urlAsset?.processing && urlAsset.processing.length > 0 && (
                <ProcessingResultsList
                  assetId={urlAssetId}
                  processing={urlAsset.processing}
                  onUseForRigging={(url, _assetId) => {
                    setRiggingSourceGlbUrl(url);
                    setSearchParams((prev) => {
                      const next = new URLSearchParams(prev);
                      next.set("tab", "rigging");
                      next.set("assetId", urlAssetId);
                      return next;
                    });
                  }}
                />
              )}
            </>
          ) : (
            <p className="pipeline-asset-context__empty">
              Wähle ein Asset aus der Bibliothek, um Mesh-Bearbeitung
              (Vereinfachen, Reparieren) durchzuführen.
            </p>
          )}
        </div>
      )}

      {assetPickerOpen && (
        <AssetPickerModal
          isOpen={true}
          onClose={() => setAssetPickerOpen(null)}
          onSelect={(asset) =>
            handleAssetPickerSelect(asset, assetPickerOpen.tab)
          }
          filter={
            assetPickerOpen.tab === "animation" ? "has_rigging" : "has_mesh"
          }
        />
      )}
      {showSketchfabImport && (
        <SketchfabImportModal onClose={() => setShowSketchfabImport(false)} />
      )}
    </main>
  );
}

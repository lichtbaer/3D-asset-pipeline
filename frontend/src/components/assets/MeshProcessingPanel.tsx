import { useState, useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  analyzeMesh,
  simplifyMesh,
  repairMesh,
  clipFloor,
  removeComponents,
  getMeshSources,
  type RepairOperation,
} from "../../api/meshProcessing.js";
import {
  getAssetFileUrl,
  deleteAssetFile,
  generateLods,
  startTextureBake,
  getTextureBakeStatus,
  type LodResult,
  type TextureBakingEntry,
} from "../../api/assets.js";
import { MeshViewer } from "../viewer/MeshViewer.js";
import type { ProcessingEntry } from "../../api/assets.js";

const RESOLUTION_OPTIONS = [512, 1024, 2048] as const;
const BAKE_TYPE_OPTIONS = [
  { value: "diffuse" as const, label: "Diffuse" },
  { value: "roughness" as const, label: "Roughness" },
  { value: "metallic" as const, label: "Metallic" },
] as const;

const SIMPLIFY_PRESETS = [500000, 100000, 50000, 10000];

const REPAIR_OPTIONS: { value: RepairOperation; label: string }[] = [
  { value: "remove_duplicates", label: "Doppelte Vertices entfernen" },
  { value: "fix_normals", label: "Normalen reparieren" },
  { value: "fill_holes", label: "Löcher schließen" },
  { value: "remove_degenerate", label: "Degenerierte Faces entfernen" },
];

const COMPONENT_RATIO_PRESETS = [
  { value: 0.05, label: "5%" },
  { value: 0.1, label: "10%" },
  { value: 0.2, label: "20%" },
];

interface MeshProcessingPanelProps {
  assetId: string;
  textureBaking?: TextureBakingEntry[];
  onUseForRigging?: (url: string, assetId: string) => void;
}

export function MeshProcessingPanel({
  assetId,
  textureBaking = [],
  onUseForRigging,
}: MeshProcessingPanelProps) {
  const queryClient = useQueryClient();
  const [sourceFile, setSourceFile] = useState("mesh.glb");
  const [customFaces, setCustomFaces] = useState("");
  const [repairOps, setRepairOps] = useState<RepairOperation[]>([
    "remove_duplicates",
    "fix_normals",
    "remove_degenerate",
  ]);
  const [clipFloorMode, setClipFloorMode] = useState<"auto" | "zero" | "custom">(
    "auto"
  );
  const [customYThreshold, setCustomYThreshold] = useState("");
  const [componentRatio, setComponentRatio] = useState(0.05);
  const [customComponentRatio, setCustomComponentRatio] = useState("");
  const [bakeSourceMesh, setBakeSourceMesh] = useState("mesh.glb");
  const [bakeTargetMesh, setBakeTargetMesh] = useState("");
  const [bakeResolution, setBakeResolution] = useState(1024);
  const [bakeTypes, setBakeTypes] = useState<string[]>([
    "diffuse",
    "roughness",
    "metallic",
  ]);
  const [bakeJobId, setBakeJobId] = useState<string | null>(null);

  const { data: sources } = useQuery({
    queryKey: ["mesh-sources", assetId],
    queryFn: () => getMeshSources(assetId),
    enabled: !!assetId,
  });

  const meshSources = useMemo(
    () =>
      (sources?.sources?.length ?? 0) > 0 ? sources!.sources : ["mesh.glb"],
    [sources]
  );
  const effectiveSource = meshSources.includes(sourceFile)
    ? sourceFile
    : meshSources[0] ?? "mesh.glb";

  const { data: analysis, isLoading: analysisLoading } = useQuery({
    queryKey: ["mesh-analysis", assetId, effectiveSource],
    queryFn: () => analyzeMesh(assetId, effectiveSource),
    enabled: !!assetId && !!effectiveSource,
  });

  const simplifyMutation = useMutation({
    mutationFn: (targetFaces: number) =>
      simplifyMesh(assetId, {
        source_file: effectiveSource,
        target_faces: targetFaces,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["mesh-sources", assetId] });
    },
  });

  const repairMutation = useMutation({
    mutationFn: () =>
      repairMesh(assetId, {
        source_file: effectiveSource,
        operations: repairOps,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["mesh-sources", assetId] });
    },
  });

  const clipFloorMutation = useMutation({
    mutationFn: () => {
      let yThreshold: number | null = null;
      if (clipFloorMode === "zero") yThreshold = 0;
      else if (clipFloorMode === "custom") {
        const v = parseFloat(customYThreshold);
        if (Number.isFinite(v)) yThreshold = v;
      }
      return clipFloor(assetId, {
        source_file: effectiveSource,
        y_threshold: yThreshold ?? undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["mesh-sources", assetId] });
    },
  });

  const removeComponentsMutation = useMutation({
    mutationFn: () => {
      let ratio = componentRatio;
      if (customComponentRatio) {
        const v = parseFloat(customComponentRatio) / 100;
        if (Number.isFinite(v) && v >= 0 && v <= 1) ratio = v;
      }
      return removeComponents(assetId, {
        source_file: effectiveSource,
        min_component_ratio: ratio,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["mesh-sources", assetId] });
    },
  });

  const lodMutation = useMutation({
    mutationFn: () =>
      generateLods(assetId, {
        source_file: effectiveSource,
        ratios: [1.0, 0.5, 0.25],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["mesh-sources", assetId] });
    },
  });

  const bakeMutation = useMutation({
    mutationFn: () =>
      startTextureBake(assetId, {
        source_mesh: bakeSourceMesh,
        target_mesh: bakeTargetMesh,
        resolution: bakeResolution,
        bake_types: bakeTypes,
      }),
    onSuccess: (data) => {
      setBakeJobId(data.job_id);
    },
  });

  const { data: bakeStatus } = useQuery({
    queryKey: ["texture-bake-status", assetId, bakeJobId],
    queryFn: () => getTextureBakeStatus(assetId, bakeJobId!),
    enabled: !!assetId && !!bakeJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "processing" ? 2000 : false;
    },
  });

  useEffect(() => {
    if (bakeStatus?.status === "done" || bakeStatus?.status === "failed") {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["mesh-sources", assetId] });
      setBakeJobId(null);
    }
  }, [bakeStatus?.status, queryClient, assetId]);

  const showTextureBaking =
    meshSources.length >= 2 && meshSources.includes("mesh.glb");

  const effectiveBakeSource = meshSources.includes(bakeSourceMesh)
    ? bakeSourceMesh
    : meshSources[0] ?? "mesh.glb";
  const effectiveBakeTarget = meshSources.includes(bakeTargetMesh)
    ? bakeTargetMesh
    : meshSources.find((f) => f !== "mesh.glb") ?? meshSources[1] ?? "";

  useEffect(() => {
    if (effectiveBakeTarget && !bakeTargetMesh) {
      setBakeTargetMesh(effectiveBakeTarget);
    }
  }, [effectiveBakeTarget, bakeTargetMesh]);

  const toggleBakeType = (t: string) => {
    setBakeTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  const handleSimplifyPreset = (targetFaces: number) => {
    simplifyMutation.mutate(targetFaces);
  };

  const handleSimplifyCustom = () => {
    const n = parseInt(customFaces, 10);
    if (Number.isFinite(n) && n > 0) {
      simplifyMutation.mutate(n);
    }
  };

  const toggleRepairOp = (op: RepairOperation) => {
    setRepairOps((prev) =>
      prev.includes(op) ? prev.filter((o) => o !== op) : [...prev, op]
    );
  };

  return (
    <section className="mesh-processing-panel">
      <h3>Mesh-Bearbeitung</h3>

      <div className="mesh-processing__source">
        <label htmlFor="mesh-source">Quelle</label>
        <select
          id="mesh-source"
          value={effectiveSource}
          onChange={(e) => setSourceFile(e.target.value)}
        >
          {meshSources.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      <div className="mesh-processing__analysis">
        <h4>Analyse</h4>
        {analysisLoading ? (
          <p>Lade Analyse…</p>
        ) : analysis ? (
          <p className="mesh-processing__stats">
            Vertices: {analysis.vertex_count.toLocaleString("de-DE")} | Faces:{" "}
            {analysis.face_count.toLocaleString("de-DE")} | Watertight:{" "}
            {analysis.is_watertight ? "✓" : "✗"} | Manifold:{" "}
            {analysis.is_manifold ? "✓" : "✗"}
          </p>
        ) : (
          <p>Keine Analyse verfügbar</p>
        )}
      </div>

      <div className="mesh-processing__simplify">
        <h4>Vereinfachen</h4>
        <div className="mesh-processing__presets">
          {SIMPLIFY_PRESETS.map((n) => (
            <button
              key={n}
              type="button"
              className="btn btn--outline btn--sm"
              onClick={() => handleSimplifyPreset(n)}
              disabled={simplifyMutation.isPending}
            >
              {n.toLocaleString("de-DE")}
            </button>
          ))}
        </div>
        <div className="mesh-processing__custom">
          <input
            type="number"
            min={1}
            placeholder="Eigener Wert"
            value={customFaces}
            onChange={(e) => setCustomFaces(e.target.value)}
            className="mesh-processing__custom-input"
          />
          <button
            type="button"
            onClick={handleSimplifyCustom}
            disabled={simplifyMutation.isPending}
          >
            Vereinfachen
          </button>
        </div>
      </div>

      <div className="mesh-processing__repair">
        <h4>Reparieren</h4>
        <div className="mesh-processing__checkboxes">
          {REPAIR_OPTIONS.map(({ value, label }) => (
            <label key={value} className="mesh-processing__checkbox">
              <input
                type="checkbox"
                checked={repairOps.includes(value)}
                onChange={() => toggleRepairOp(value)}
              />
              {label}
            </label>
          ))}
        </div>
        <button
          type="button"
          onClick={() => repairMutation.mutate()}
          disabled={repairMutation.isPending || repairOps.length === 0}
        >
          {repairMutation.isPending ? "Reparieren…" : "Reparieren"}
        </button>
      </div>

      <div className="mesh-processing__artifact-cleanup">
        <h4>Artefakt-Bereinigung</h4>

        <div className="mesh-processing__clip-floor">
          <p className="mesh-processing__subsection-title">Boden entfernen</p>
          <p className="mesh-processing__info">
            ℹ Empfohlen vor dem Rigging wenn der Mesh auf einem Boden oder
            Sockel steht.
          </p>
          <div className="mesh-processing__presets">
            <button
              type="button"
              className={`btn btn--outline btn--sm ${clipFloorMode === "auto" ? "btn--active" : ""}`}
              onClick={() => setClipFloorMode("auto")}
            >
              Auto
            </button>
            <button
              type="button"
              className={`btn btn--outline btn--sm ${clipFloorMode === "zero" ? "btn--active" : ""}`}
              onClick={() => setClipFloorMode("zero")}
            >
              0.0
            </button>
            <input
              type="number"
              step="any"
              placeholder="Eigener Wert"
              value={customYThreshold}
              onChange={(e) => {
                setCustomYThreshold(e.target.value);
                setClipFloorMode("custom");
              }}
              className="mesh-processing__custom-input"
            />
          </div>
          <button
            type="button"
            onClick={() => clipFloorMutation.mutate()}
            disabled={clipFloorMutation.isPending}
          >
            {clipFloorMutation.isPending ? "Boden abschneiden…" : "Boden abschneiden"}
          </button>
        </div>

        <div className="mesh-processing__remove-components">
          <p className="mesh-processing__subsection-title">
            Isolierte Teile entfernen
          </p>
          <div className="mesh-processing__presets">
            {COMPONENT_RATIO_PRESETS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={`btn btn--outline btn--sm ${componentRatio === value && !customComponentRatio ? "btn--active" : ""}`}
                onClick={() => {
                  setComponentRatio(value);
                  setCustomComponentRatio("");
                }}
              >
                {label}
              </button>
            ))}
            <input
              type="number"
              min={0}
              max={100}
              step={0.1}
              placeholder="Eigener Wert %"
              value={customComponentRatio}
              onChange={(e) => setCustomComponentRatio(e.target.value)}
              className="mesh-processing__custom-input"
            />
          </div>
          <button
            type="button"
            onClick={() => removeComponentsMutation.mutate()}
            disabled={removeComponentsMutation.isPending}
          >
            {removeComponentsMutation.isPending
              ? "Kleine Teile entfernen…"
              : "Kleine Teile entfernen"}
          </button>
        </div>
      </div>

      <div className="mesh-processing__lod">
        <h4>Level of Detail (LOD)</h4>
        <p className="mesh-processing__info">
          ℹ Erzeugt 3 Varianten: LOD0 (Original), LOD1 (50%), LOD2 (25% Faces).
          Optimal für Game-Engine-Workflows.
        </p>
        <button
          type="button"
          className="btn btn--outline"
          onClick={() => lodMutation.mutate()}
          disabled={lodMutation.isPending}
        >
          {lodMutation.isPending ? "LODs generieren…" : "LODs generieren"}
        </button>
        {lodMutation.isError && (
          <p className="mesh-processing__error">
            Fehler: {lodMutation.error instanceof Error ? lodMutation.error.message : "Unbekannter Fehler"}
          </p>
        )}
        {lodMutation.isSuccess && lodMutation.data && (
          <ul className="mesh-processing__results-list">
            {lodMutation.data.lods.map((lod: LodResult) => (
              <li key={lod.level} className="mesh-processing__result-item mesh-processing__result-item--inline">
                <span className="mesh-processing__result-label">
                  LOD{lod.level}: {lod.output_file} — {lod.actual_faces.toLocaleString("de-DE")} Faces ({Math.round(lod.ratio * 100)}%)
                </span>
                <a
                  href={getAssetFileUrl(assetId, lod.output_file)}
                  download
                  className="asset-modal__download"
                >
                  Download
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>

      {showTextureBaking && (
        <div className="mesh-processing__texture-baking">
          <h4>Textur-Rebaking</h4>
          <p className="mesh-processing__info">
            ℹ Empfohlen nach Simplification um PBR-Texturen zu erhalten.
            Laufzeit: ca. 30–120s je nach Mesh-Komplexität.
          </p>
          <div className="mesh-processing__texture-baking-fields">
            <div className="mesh-processing__source">
              <label htmlFor="bake-source">Textur-Quelle (High-Poly)</label>
              <select
                id="bake-source"
                value={effectiveBakeSource}
                onChange={(e) => setBakeSourceMesh(e.target.value)}
              >
                {meshSources.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
            <div className="mesh-processing__source">
              <label htmlFor="bake-target">Ziel-Mesh (Low-Poly)</label>
              <select
                id="bake-target"
                value={effectiveBakeTarget}
                onChange={(e) => setBakeTargetMesh(e.target.value)}
              >
                {meshSources
                  .filter((f) => f !== effectiveBakeSource)
                  .map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
              </select>
            </div>
            <div className="mesh-processing__texture-baking-resolution">
              <label>Auflösung</label>
              <div className="mesh-processing__presets">
                {RESOLUTION_OPTIONS.map((r) => (
                  <button
                    key={r}
                    type="button"
                    className={`btn btn--outline btn--sm ${bakeResolution === r ? "btn--active" : ""}`}
                    onClick={() => setBakeResolution(r)}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <div className="mesh-processing__texture-baking-types">
              <label>Bake-Typen</label>
              <div className="mesh-processing__checkboxes">
                {BAKE_TYPE_OPTIONS.map(({ value, label }) => (
                  <label key={value} className="mesh-processing__checkbox">
                    <input
                      type="checkbox"
                      checked={bakeTypes.includes(value)}
                      onChange={() => toggleBakeType(value)}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <button
            type="button"
            className="btn btn--outline"
            onClick={() => bakeMutation.mutate()}
            disabled={
              bakeMutation.isPending ||
              !!bakeJobId ||
              bakeTypes.length === 0 ||
              effectiveBakeSource === effectiveBakeTarget
            }
          >
            {bakeMutation.isPending || bakeJobId
              ? `Baking läuft…${bakeStatus?.duration_seconds ? ` (${Math.round(bakeStatus.duration_seconds)}s)` : ""}`
              : "Texturen baken"}
          </button>
          {bakeStatus?.status === "failed" && bakeStatus.error_msg && (
            <p className="mesh-processing__error">{bakeStatus.error_msg}</p>
          )}
          {bakeStatus?.status === "done" && bakeStatus.output_file && (
            <div className="mesh-processing__bake-result">
              <p className="mesh-processing__result-label">
                Ergebnis: {bakeStatus.output_file}
              </p>
              <div className="mesh-processing__result-actions">
                <a
                  href={getAssetFileUrl(assetId, bakeStatus.output_file)}
                  download
                  className="asset-modal__download"
                >
                  Download
                </a>
                {onUseForRigging && (
                  <button
                    type="button"
                    className="btn btn--outline"
                    onClick={() =>
                      onUseForRigging(
                        getAssetFileUrl(assetId, bakeStatus.output_file),
                        assetId
                      )
                    }
                  >
                    → Als Rigging-Input verwenden
                  </button>
                )}
              </div>
            </div>
          )}
          {textureBaking.length > 0 && (
            <div className="mesh-processing__texture-baking-results">
              <p className="mesh-processing__subsection-title">
                Bisher gebackene Texturen
              </p>
              <ul className="mesh-processing__results-list">
                {textureBaking.map((tb, i) => (
                  <li key={i} className="mesh-processing__result-item">
                    <div className="mesh-processing__result-preview">
                      <MeshViewer
                        glbUrl={getAssetFileUrl(assetId, tb.output_file)}
                        height={200}
                        readOnly
                      />
                    </div>
                    <p className="mesh-processing__result-label">
                      {tb.output_file}
                    </p>
                    <div className="mesh-processing__result-actions">
                      <a
                        href={getAssetFileUrl(assetId, tb.output_file)}
                        download
                        className="asset-modal__download"
                      >
                        Download
                      </a>
                      {onUseForRigging && (
                        <button
                          type="button"
                          className="btn btn--outline"
                          onClick={() =>
                            onUseForRigging(
                              getAssetFileUrl(assetId, tb.output_file),
                              assetId
                            )
                          }
                        >
                          → Als Rigging-Input verwenden
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

interface ProcessingResultsListProps {
  assetId: string;
  processing: ProcessingEntry[];
  onUseForRigging: (url: string, assetId: string) => void;
}

export function ProcessingResultsList({
  assetId,
  processing,
  onUseForRigging,
}: ProcessingResultsListProps) {
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => deleteAssetFile(assetId, filename),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["mesh-sources", assetId] });
      setConfirmDelete(null);
    },
  });

  const uniqueOutputs = [
    ...new Set(
      processing
        .map((e) => ("output_file" in e ? e.output_file : null))
        .filter((f): f is string => !!f)
    ),
  ];

  if (uniqueOutputs.length === 0) return null;

  return (
    <div className="mesh-processing__results">
      <h4>Verarbeitete Dateien</h4>
      <ul className="mesh-processing__results-list">
        {uniqueOutputs.map((filename) => {
          const url = getAssetFileUrl(assetId, filename);
          const isConfirming = confirmDelete === filename;
          return (
            <li key={filename} className="mesh-processing__result-item">
              <div className="mesh-processing__result-preview">
                <MeshViewer glbUrl={url} height={200} readOnly />
              </div>
              <p className="mesh-processing__result-label">{filename}</p>
              <div className="mesh-processing__result-actions">
                <a href={url} download className="asset-modal__download">
                  Download
                </a>
                <button
                  type="button"
                  className="btn btn--outline"
                  onClick={() => onUseForRigging(url, assetId)}
                >
                  → Als Rigging-Input verwenden
                </button>
                {isConfirming ? (
                  <span className="mesh-processing__delete-confirm">
                    <span className="mesh-processing__delete-text">
                      {filename} löschen? Nicht rückgängig.
                    </span>
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={() => setConfirmDelete(null)}
                    >
                      Abbrechen
                    </button>
                    <button
                      type="button"
                      className="btn btn--danger btn--sm"
                      onClick={() => deleteMutation.mutate(filename)}
                      disabled={deleteMutation.isPending}
                    >
                      Löschen
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm mesh-processing__delete-btn"
                    onClick={() => setConfirmDelete(filename)}
                    aria-label={`${filename} löschen`}
                    title={`${filename} löschen`}
                  >
                    🗑
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

import { useState, useMemo } from "react";
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
} from "../../api/assets.js";
import { MeshViewer } from "../viewer/MeshViewer.js";
import type { ProcessingEntry } from "../../api/assets.js";

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
}

export function MeshProcessingPanel({ assetId }: MeshProcessingPanelProps) {
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

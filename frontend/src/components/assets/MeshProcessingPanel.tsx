import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  analyzeMesh,
  simplifyMesh,
  repairMesh,
  getMeshSources,
  type RepairOperation,
} from "../../api/meshProcessing.js";
import { getAssetFileUrl } from "../../api/assets.js";
import { MeshViewer } from "../viewer/MeshViewer.js";
import type { ProcessingEntry } from "../../api/assets.js";

const SIMPLIFY_PRESETS = [500000, 100000, 50000, 10000];

const REPAIR_OPTIONS: { value: RepairOperation; label: string }[] = [
  { value: "remove_duplicates", label: "Doppelte Vertices entfernen" },
  { value: "fix_normals", label: "Normalen reparieren" },
  { value: "fill_holes", label: "Löcher schließen" },
  { value: "remove_degenerate", label: "Degenerierte Faces entfernen" },
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
              className="mesh-processing__preset-btn"
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
                  className="asset-modal__action-btn"
                  onClick={() => onUseForRigging(url, assetId)}
                >
                  → Als Rigging-Input verwenden
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  exportMesh,
  getAssetExports,
  getAssetFileUrl,
  deleteAssetFile,
  checkPrintReadiness,
  type PrintReadinessReport,
} from "../../api/assets.js";
import { getMeshSources } from "../../api/meshProcessing.js";
import type { ExportListItem } from "../../api/assets.js";

const EXPORT_FORMATS = [
  { value: "stl" as const, label: "STL" },
  { value: "obj" as const, label: "OBJ" },
  { value: "ply" as const, label: "PLY" },
  { value: "gltf" as const, label: "GLTF" },
] as const;

const FORMAT_INFO: Record<string, string> = {
  stl: "Keine Texturen. Standard für 3D-Druck.",
  obj: "Mit Materialien (.mtl). Universell kompatibel.",
  ply: "Mit Vertex-Farben wenn vorhanden. Gut für MeshLab.",
  gltf: "Entpacktes GLB-Format. Für Web und Three.js.",
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface ExportPanelProps {
  assetId: string;
}

export function ExportPanel({ assetId }: ExportPanelProps) {
  const queryClient = useQueryClient();
  const [format, setFormat] = useState<"stl" | "obj" | "ply" | "gltf">("stl");
  const [sourceFile, setSourceFile] = useState("mesh.glb");
  const [printReport, setPrintReport] = useState<PrintReadinessReport | null>(null);

  const { data: sourcesData } = useQuery({
    queryKey: ["mesh-sources", assetId],
    queryFn: () => getMeshSources(assetId),
    enabled: !!assetId,
  });

  const meshSources = useMemo(
    () =>
      (sourcesData?.sources?.length ?? 0) > 0
        ? sourcesData!.sources
        : ["mesh.glb"],
    [sourcesData]
  );

  const effectiveSource = meshSources.includes(sourceFile)
    ? sourceFile
    : meshSources[0] ?? "mesh.glb";

  const { data: exportsData } = useQuery({
    queryKey: ["asset-exports", assetId],
    queryFn: () => getAssetExports(assetId),
    enabled: !!assetId,
  });

  const exportsList: ExportListItem[] = exportsData?.exports ?? [];
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => deleteAssetFile(assetId, filename),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["asset-exports", assetId] });
      setConfirmDelete(null);
    },
  });

  const exportMutation = useMutation({
    mutationFn: () =>
      exportMesh(assetId, {
        source_file: effectiveSource,
        format,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["asset-exports", assetId] });
    },
  });

  const printReadinessMutation = useMutation({
    mutationFn: () => checkPrintReadiness(assetId, effectiveSource),
    onSuccess: (report) => setPrintReport(report),
  });

  return (
    <section className="export-panel">
      <h3>Export</h3>

      <div className="export-panel__formats">
        <span className="export-panel__label">Format:</span>
        <div className="export-panel__format-buttons">
          {EXPORT_FORMATS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              className={`btn btn--outline btn--sm ${
                format === value ? "btn--active" : ""
              }`}
              onClick={() => setFormat(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="export-panel__source">
        <label htmlFor="export-source">Quelle</label>
        <select
          id="export-source"
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

      <p className="export-panel__info">ℹ {FORMAT_INFO[format]}</p>

      <button
        type="button"
        className="btn btn--primary"
        onClick={() => exportMutation.mutate()}
        disabled={exportMutation.isPending}
      >
        {exportMutation.isPending ? "Exportieren…" : "Exportieren"}
      </button>

      {exportMutation.isError && (
        <p className="export-panel__error">
          {exportMutation.error instanceof Error
            ? exportMutation.error.message
            : "Export fehlgeschlagen"}
        </p>
      )}

      <div className="export-panel__print-readiness">
        <button
          type="button"
          className="btn btn--outline btn--sm"
          onClick={() => {
            setPrintReport(null);
            printReadinessMutation.mutate();
          }}
          disabled={printReadinessMutation.isPending}
        >
          {printReadinessMutation.isPending ? "Prüfe…" : "🖨 Druckeignung prüfen"}
        </button>
        {printReport && (
          <div className="export-panel__print-report">
            <span
              className={`export-panel__print-badge ${
                printReport.print_ready
                  ? "export-panel__print-badge--ok"
                  : "export-panel__print-badge--fail"
              }`}
            >
              {printReport.print_ready ? "✓ Druckbereit" : "✗ Nicht druckbereit"}
            </span>
            <ul className="export-panel__print-checks">
              {printReport.checks.map((c) => (
                <li key={c.name} className="export-panel__print-check">
                  <span>{c.passed ? "✓" : "✗"}</span>
                  <strong>{c.name}</strong>
                  <span className="export-panel__print-desc">{c.description}</span>
                </li>
              ))}
            </ul>
            <p className="export-panel__print-stats">
              {printReport.stats.face_count.toLocaleString()} Faces ·{" "}
              {printReport.stats.width_mm.toFixed(1)} ×{" "}
              {printReport.stats.height_mm.toFixed(1)} ×{" "}
              {printReport.stats.depth_mm.toFixed(1)} mm
            </p>
          </div>
        )}
        {printReadinessMutation.isError && (
          <p className="export-panel__error">Druckeignungsprüfung fehlgeschlagen</p>
        )}
      </div>

      {exportsList.length > 0 && (
        <div className="export-panel__exports">
          <h4>Vorhandene Exports</h4>
          <ul className="export-panel__exports-list">
            {exportsList.map((exp) => {
              const isConfirming = confirmDelete === exp.filename;
              return (
                <li
                  key={`${exp.filename}-${exp.exported_at}`}
                  className="export-panel__export-item"
                >
                  <span className="export-panel__export-name">{exp.filename}</span>
                  <span className="export-panel__export-size">
                    {formatFileSize(exp.file_size_bytes)}
                  </span>
                  <a
                    href={getAssetFileUrl(assetId, exp.filename)}
                    download
                    className="asset-modal__download"
                  >
                    ↓ Download
                  </a>
                  {isConfirming ? (
                    <span className="export-panel__delete-confirm">
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
                        onClick={() => deleteMutation.mutate(exp.filename)}
                        disabled={deleteMutation.isPending}
                      >
                        Löschen
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm export-panel__delete-btn"
                      onClick={() => setConfirmDelete(exp.filename)}
                      aria-label={`${exp.filename} löschen`}
                      title={`${exp.filename} löschen`}
                    >
                      🗑
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}

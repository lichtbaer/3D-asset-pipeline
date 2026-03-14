import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSketchfabStatus,
  uploadToSketchfab,
  getSketchfabUploadStatus,
} from "../../api/sketchfab.js";
import { getMeshSources } from "../../api/meshProcessing.js";
import type { SketchfabUploadInfo } from "../../api/assets.js";

interface SketchfabPanelProps {
  assetId: string;
  assetName?: string;
  sketchfabUpload?: SketchfabUploadInfo | null;
  onAssetUpdate?: () => void;
}

export function SketchfabPanel({
  assetId,
  assetName = "",
  sketchfabUpload,
  onAssetUpdate,
}: SketchfabPanelProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState(assetName || `Asset ${assetId.slice(0, 8)}`);
  const [description, setDescription] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [isPrivate, setIsPrivate] = useState(false);
  const [sourceFile, setSourceFile] = useState("mesh.glb");

  const { data: sketchfabEnabled } = useQuery({
    queryKey: ["sketchfab-status"],
    queryFn: getSketchfabStatus,
  });

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

  const { data: uploadStatus } = useQuery({
    queryKey: ["sketchfab-upload-status", assetId],
    queryFn: () => getSketchfabUploadStatus(assetId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" || status === "none"
        ? false
        : 3000;
    },
    enabled: !!assetId && !!sketchfabEnabled?.enabled,
  });

  const uploadMutation = useMutation({
    mutationFn: () =>
      uploadToSketchfab(assetId, {
        name: name.trim() || `Asset ${assetId.slice(0, 8)}`,
        description: description.trim(),
        tags: tagsInput
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        is_private: isPrivate,
        source_file: effectiveSource,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sketchfab-upload-status", assetId] });
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      onAssetUpdate?.();
    },
  });

  const resolvedUpload = sketchfabUpload ?? (uploadStatus?.status === "done" && uploadStatus?.sketchfab_url
    ? {
        uid: uploadStatus.sketchfab_uid ?? "",
        url: uploadStatus.sketchfab_url,
        embed_url: uploadStatus.embed_url ?? "",
        uploaded_at: "",
      }
    : null);
  const isUploading =
    uploadStatus?.status === "pending" || uploadStatus?.status === "processing";
  const uploadError = uploadStatus?.error_msg;

  if (!sketchfabEnabled?.enabled) {
    return null;
  }

  return (
    <section className="sketchfab-panel">
      <h3>Sketchfab</h3>

      {resolvedUpload?.url ? (
        <div className="sketchfab-panel__uploaded">
          <p>Bereits hochgeladen:</p>
          <a
            href={resolvedUpload.url}
            target="_blank"
            rel="noopener noreferrer"
            className="sketchfab-panel__link"
          >
            {resolvedUpload.url}
          </a>
          <a
            href={resolvedUpload.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn--outline btn--sm"
          >
            Link öffnen
          </a>
        </div>
      ) : (
        <>
          <div className="sketchfab-panel__form">
            <div className="sketchfab-panel__field">
              <label htmlFor="sketchfab-name">Name</label>
              <input
                id="sketchfab-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Asset-Name"
              />
            </div>
            <div className="sketchfab-panel__field">
              <label htmlFor="sketchfab-desc">Beschreibung</label>
              <input
                id="sketchfab-desc"
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="optional"
              />
            </div>
            <div className="sketchfab-panel__field">
              <label htmlFor="sketchfab-tags">Tags</label>
              <input
                id="sketchfab-tags"
                type="text"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="scan, character, purzel"
              />
            </div>
            <div className="sketchfab-panel__field sketchfab-panel__radio">
              <span>Sichtbarkeit</span>
              <label>
                <input
                  type="radio"
                  checked={!isPrivate}
                  onChange={() => setIsPrivate(false)}
                />
                Öffentlich
              </label>
              <label>
                <input
                  type="radio"
                  checked={isPrivate}
                  onChange={() => setIsPrivate(true)}
                />
                Privat
              </label>
            </div>
            <div className="sketchfab-panel__field">
              <label htmlFor="sketchfab-source">Quelle</label>
              <select
                id="sketchfab-source"
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
          </div>

          {uploadError && (
            <p className="sketchfab-panel__error">{uploadError}</p>
          )}

          {isUploading ? (
            <div className="sketchfab-panel__status">
              <div className="spinner" aria-hidden />
              <p>Hochladen läuft…</p>
            </div>
          ) : (
            <button
              type="button"
              className="btn btn--outline"
              onClick={() => uploadMutation.mutate()}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? "Hochladen…" : "Hochladen"}
            </button>
          )}
        </>
      )}
    </section>
  );
}

import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  uploadImage,
  uploadMesh,
  type UploadImageOptions,
  type UploadMeshOptions,
} from "../../api/assets.js";
import { useToast } from "../ui/ToastContext.js";

const IMAGE_ACCEPT = ".jpg,.jpeg,.png,.webp";
const IMAGE_MAX_MB = 20;
const MESH_ACCEPT = ".glb,.gltf,.obj,.ply,.stl,.zip";
const MESH_MAX_MB = 100;

const IMAGE_EXT = new Set([".jpg", ".jpeg", ".png", ".webp"]);
const MESH_EXT = new Set([".glb", ".gltf", ".obj", ".ply", ".stl", ".zip"]);

function getExt(filename: string): string {
  const i = filename.lastIndexOf(".");
  return i >= 0 ? filename.slice(i).toLowerCase() : "";
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export type UploadType = "image" | "mesh";

export interface AssetUploadZoneProps {
  type: UploadType;
  onSuccess?: (assetId: string, file?: string) => void;
  compact?: boolean;
}

export function AssetUploadZone({
  type,
  onSuccess,
  compact = false,
}: AssetUploadZoneProps) {
  const [file, setFile] = useState<File | null>(null);
  const [mtlFile, setMtlFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const isImage = type === "image";
  const accept = isImage ? IMAGE_ACCEPT : MESH_ACCEPT;
  const maxMb = isImage ? IMAGE_MAX_MB : MESH_MAX_MB;
  const label = isImage ? "Bild hochladen" : "3D-Modell hochladen";

  const validateFile = useCallback(
    (f: File): string | null => {
      const ext = getExt(f.name);
      const allowed = isImage ? IMAGE_EXT : MESH_EXT;
      if (!allowed.has(ext)) {
        return `Ungültiges Format. Erlaubt: ${accept}`;
      }
      const maxBytes = maxMb * 1024 * 1024;
      if (f.size > maxBytes) {
        return `Datei zu groß. Maximum: ${maxMb} MB`;
      }
      return null;
    },
    [isImage, accept, maxMb]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setError(null);
      const dropped = e.dataTransfer.files;
      if (!dropped.length) return;
      const f = dropped[0];
      const err = validateFile(f);
      if (err) {
        setError(err);
        return;
      }
      setFile(f);
      if (!isImage && f.name.toLowerCase().endsWith(".obj")) {
        const mtl = Array.from(dropped).find(
          (x) => x.name.toLowerCase().endsWith(".mtl")
        );
        setMtlFile(mtl ?? null);
      } else {
        setMtlFile(null);
      }
    },
    [validateFile, isImage]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setError(null);
      const f = e.target.files?.[0];
      if (!f) return;
      const err = validateFile(f);
      if (err) {
        setError(err);
        return;
      }
      setFile(f);
      setMtlFile(null);
      e.target.value = "";
    },
    [validateFile]
  );

  const handleMtlChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (!f) return;
      if (f.name.toLowerCase().endsWith(".mtl")) {
        setMtlFile(f);
      }
      e.target.value = "";
    },
    []
  );

  const handleUpload = useCallback(async () => {
    if (!file || uploading) return;
    setUploading(true);
    setError(null);
    setProgress(0);
    try {
      if (isImage) {
        const res = await uploadImage({
          file,
          onProgress: setProgress,
        } as UploadImageOptions);
        addToast("Bild hochgeladen!", "success");
        queryClient.invalidateQueries({ queryKey: ["assets"] });
        queryClient.invalidateQueries({ queryKey: ["asset", res.asset_id] });
        setFile(null);
        setProgress(null);
        onSuccess?.(res.asset_id, res.file);
      } else {
        const res = await uploadMesh({
          file,
          mtlFile: mtlFile ?? undefined,
          onProgress: setProgress,
        } as UploadMeshOptions);
        addToast("3D-Modell hochgeladen!", "success");
        queryClient.invalidateQueries({ queryKey: ["assets"] });
        queryClient.invalidateQueries({ queryKey: ["asset", res.asset_id] });
        setFile(null);
        setMtlFile(null);
        setProgress(null);
        onSuccess?.(res.asset_id, res.file);
      }
    } catch (err) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? String(
              (err as { response?: { data?: { detail?: string } } }).response
                ?.data?.detail ?? "Upload fehlgeschlagen"
            )
          : err instanceof Error
            ? err.message
            : "Upload fehlgeschlagen";
      setError(msg);
      addToast(msg, "error");
    } finally {
      setUploading(false);
    }
  }, [file, mtlFile, isImage, uploading, addToast, queryClient, onSuccess]);

  const handleClear = useCallback(() => {
    setFile(null);
    setMtlFile(null);
    setError(null);
    setProgress(null);
  }, []);

  if (compact) {
    return (
      <div className="asset-upload-zone asset-upload-zone--compact">
        {!file ? (
          <label className="asset-upload-zone__compact-btn">
            <input
              type="file"
              accept={accept}
              onChange={handleFileChange}
              className="asset-upload-zone__hidden-input"
              aria-label={label}
            />
            <span>↑ {label}</span>
          </label>
        ) : (
          <div className="asset-upload-zone__compact-selected">
            <span className="asset-upload-zone__compact-filename">{file.name}</span>
            {progress !== null && (
              <div className="asset-upload-zone__progress asset-upload-zone__progress--sm">
                <div
                  className="asset-upload-zone__progress-bar"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
            {!uploading && (
              <div className="asset-upload-zone__compact-actions">
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={handleUpload}
                >
                  Hochladen
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={handleClear}
                >
                  Abbrechen
                </button>
              </div>
            )}
          </div>
        )}
        {error && (
          <p className="asset-upload-zone__error asset-upload-zone__error--sm" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <div
      className="asset-upload-zone"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      <div className="asset-upload-zone__drop">
        <p className="asset-upload-zone__hint">
          {isImage
            ? "JPG, PNG, WebP (max. 20 MB)"
            : "GLB, GLTF, OBJ, PLY, STL, ZIP (max. 100 MB)"}
        </p>
        <label className="asset-upload-zone__browse">
          <input
            type="file"
            accept={accept}
            onChange={handleFileChange}
            className="asset-upload-zone__hidden-input"
            aria-label={label}
          />
          Datei auswählen
        </label>
      </div>
      {!isImage && file?.name.toLowerCase().endsWith(".obj") && (
        <div className="asset-upload-zone__mtl">
          <label className="asset-upload-zone__mtl-label">
            MTL-Datei (optional):
            <input
              type="file"
              accept=".mtl"
              onChange={handleMtlChange}
              className="asset-upload-zone__hidden-input"
            />
            <span className="asset-upload-zone__mtl-link">
              {mtlFile ? mtlFile.name : "Hinzufügen"}
            </span>
          </label>
        </div>
      )}
      {file && (
        <div className="asset-upload-zone__selected">
          <span className="asset-upload-zone__filename">
            {file.name} ({formatSize(file.size)})
          </span>
          {progress !== null && (
            <div className="asset-upload-zone__progress">
              <div
                className="asset-upload-zone__progress-bar"
                style={{ width: `${progress}%` }}
              />
              <span className="asset-upload-zone__progress-text">{progress}%</span>
            </div>
          )}
          {!uploading && (
            <div className="asset-upload-zone__actions">
              <button
                type="button"
                className="btn btn--primary btn--sm"
                onClick={handleUpload}
              >
                Hochladen
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={handleClear}
              >
                Abbrechen
              </button>
            </div>
          )}
        </div>
      )}
      {error && (
        <p className="asset-upload-zone__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

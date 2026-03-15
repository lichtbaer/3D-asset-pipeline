import { useState, useCallback, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getImageSources,
  cropImage,
  resizeImage,
  centerImage,
  padSquareImage,
} from "../../api/imageProcessing.js";
import {
  getAssetFileUrl,
  getAsset,
  type ImageProcessingEntry,
} from "../../api/assets.js";

interface ImageEditorProps {
  assetId: string;
  onUseForMesh: (imageUrl: string) => void;
}

export function ImageEditor({ assetId, onUseForMesh }: ImageEditorProps) {
  const queryClient = useQueryClient();
  const [sourceFile, setSourceFile] = useState("");
  const [cropCoords, setCropCoords] = useState({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });
  const [resizeWidth, setResizeWidth] = useState(512);
  const [resizeHeight, setResizeHeight] = useState(512);
  const [maintainAspect, setMaintainAspect] = useState(true);
  const [cropDragging, setCropDragging] = useState(false);
  const [cropStart, setCropStart] = useState<{ x: number; y: number } | null>(
    null
  );
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });
  const imgRef = useRef<HTMLImageElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const { data: sourcesData } = useQuery({
    queryKey: ["image-sources", assetId],
    queryFn: () => getImageSources(assetId),
    enabled: !!assetId,
  });

  const sources = sourcesData?.sources ?? [];

  useEffect(() => {
    if (sources.length === 0) return;
    const preferred =
      sources.includes("image_bgremoved.png")
        ? "image_bgremoved.png"
        : sources.includes("image.png")
          ? "image.png"
          : sources[0];
    if (preferred && !sources.includes(sourceFile)) {
      setSourceFile(preferred);
    }
  }, [sources, sourceFile]);
  /** Bevorzuge image_bgremoved.png, sonst image.png, sonst erstes verfügbares */
  const preferredSource =
    sources.includes("image_bgremoved.png")
      ? "image_bgremoved.png"
      : sources.includes("image.png")
        ? "image.png"
        : sources[0] ?? "";
  const effectiveSource =
    sources.includes(sourceFile) ? sourceFile : preferredSource;
  const previewUrl = effectiveSource
    ? getAssetFileUrl(assetId, effectiveSource)
    : "";

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
    queryClient.invalidateQueries({ queryKey: ["image-sources", assetId] });
  }, [queryClient, assetId]);

  const centerMutation = useMutation({
    mutationFn: () =>
      centerImage(assetId, { source_file: effectiveSource, padding: 0.1 }),
    onSuccess: invalidate,
  });

  const padSquareMutation = useMutation({
    mutationFn: () =>
      padSquareImage(assetId, {
        source_file: effectiveSource,
        background: "white",
      }),
    onSuccess: invalidate,
  });

  const resize512Mutation = useMutation({
    mutationFn: () =>
      resizeImage(assetId, {
        source_file: effectiveSource,
        width: 512,
        height: 512,
        maintain_aspect: true,
      }),
    onSuccess: invalidate,
  });

  const resize1024Mutation = useMutation({
    mutationFn: () =>
      resizeImage(assetId, {
        source_file: effectiveSource,
        width: 1024,
        height: 1024,
        maintain_aspect: true,
      }),
    onSuccess: invalidate,
  });

  const cropMutation = useMutation({
    mutationFn: (coords: { x: number; y: number; width: number; height: number }) =>
      cropImage(assetId, {
        source_file: effectiveSource,
        ...coords,
      }),
    onSuccess: invalidate,
  });

  const resizeMutation = useMutation({
    mutationFn: () =>
      resizeImage(assetId, {
        source_file: effectiveSource,
        width: resizeWidth,
        height: resizeHeight,
        maintain_aspect: maintainAspect,
      }),
    onSuccess: invalidate,
  });

  const handleImageLoad = useCallback(() => {
    const img = imgRef.current;
    if (!img || !img.complete) return;
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    setImageSize({ width: w, height: h });
    setCropCoords({ x: 0, y: 0, width: w, height: h });
  }, []);

  const displayToImageCoords = useCallback(
    (displayX: number, displayY: number) => {
      const img = imgRef.current;
      if (!img || !img.complete) return { x: 0, y: 0 };
      const rect = img.getBoundingClientRect();
      const relX = (displayX - rect.left) / rect.width;
      const relY = (displayY - rect.top) / rect.height;
      return {
        x: Math.round(relX * img.naturalWidth),
        y: Math.round(relY * img.naturalHeight),
      };
    },
    []
  );

  const handleCropMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!imgRef.current) return;
      const { x, y } = displayToImageCoords(e.clientX, e.clientY);
      setCropStart({ x, y });
      setCropDragging(true);
      setCropCoords((prev) => ({ ...prev, x, y, width: 0, height: 0 }));
    },
    [displayToImageCoords]
  );

  const handleCropMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!cropDragging || !cropStart || !imgRef.current) return;
      const { x, y } = displayToImageCoords(e.clientX, e.clientY);
      const minX = Math.min(cropStart.x, x);
      const minY = Math.min(cropStart.y, y);
      const maxX = Math.max(cropStart.x, x);
      const maxY = Math.max(cropStart.y, y);
      setCropCoords({
        x: Math.max(0, minX),
        y: Math.max(0, minY),
        width: Math.min(imgRef.current.naturalWidth - minX, maxX - minX),
        height: Math.min(imgRef.current.naturalHeight - minY, maxY - minY),
      });
    },
    [cropDragging, cropStart, displayToImageCoords]
  );

  const handleCropMouseUp = useCallback(() => {
    setCropDragging(false);
    setCropStart(null);
  }, []);

  useEffect(() => {
    if (!cropDragging) return;
    const onMouseUp = () => {
      setCropDragging(false);
      setCropStart(null);
    };
    const onMouseMove = (e: MouseEvent) => {
      if (cropStart && imgRef.current) {
        const rect = imgRef.current.getBoundingClientRect();
        const nw = imgRef.current.naturalWidth;
        const nh = imgRef.current.naturalHeight;
        const x = Math.round(
          ((e.clientX - rect.left) / rect.width) * nw
        );
        const y = Math.round(
          ((e.clientY - rect.top) / rect.height) * nh
        );
        const minX = Math.max(0, Math.min(cropStart.x, x));
        const minY = Math.max(0, Math.min(cropStart.y, y));
        const maxX = Math.min(nw, Math.max(cropStart.x, x));
        const maxY = Math.min(nh, Math.max(cropStart.y, y));
        setCropCoords({
          x: minX,
          y: minY,
          width: Math.max(1, maxX - minX),
          height: Math.max(1, maxY - minY),
        });
      }
    };
    window.addEventListener("mouseup", onMouseUp);
    window.addEventListener("mousemove", onMouseMove);
    return () => {
      window.removeEventListener("mouseup", onMouseUp);
      window.removeEventListener("mousemove", onMouseMove);
    };
  }, [cropDragging, cropStart]);

  const handleCropSubmit = useCallback(() => {
    if (cropCoords.width < 1 || cropCoords.height < 1) return;
    cropMutation.mutate(cropCoords);
  }, [cropCoords, cropMutation]);

  const { data: assetData } = useQuery({
    queryKey: ["asset", assetId],
    queryFn: () => getAsset(assetId),
    enabled: !!assetId,
  });

  const imageProcessingEntries =
    (assetData?.image_processing as ImageProcessingEntry[] | undefined) ?? [];
  const allImageFiles = [
    ...new Set([
      ...sources,
      ...imageProcessingEntries.map((e) => e.output_file),
    ]),
  ].filter(Boolean);

  /** Zuletzt bearbeitetes Bild: letzter Processing-Output oder Quelle */
  const lastEditedFile =
    imageProcessingEntries.length > 0
      ? imageProcessingEntries[imageProcessingEntries.length - 1].output_file
      : effectiveSource;
  const lastEditedUrl = lastEditedFile
    ? getAssetFileUrl(assetId, lastEditedFile)
    : "";

  if (sources.length === 0) return null;

  const isPending =
    centerMutation.isPending ||
    padSquareMutation.isPending ||
    resize512Mutation.isPending ||
    resize1024Mutation.isPending ||
    cropMutation.isPending ||
    resizeMutation.isPending;

  return (
    <section className="image-editor pipeline-page__section">
      <h2>Bild nachbearbeiten</h2>

      <div className="form-group">
        <label htmlFor="image-editor-source">Quelle</label>
        <select
          id="image-editor-source"
          value={effectiveSource}
          onChange={(e) => setSourceFile(e.target.value)}
        >
          {sources.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      {previewUrl && (
        <>
          <div className="image-editor__quick-actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => centerMutation.mutate()}
              disabled={isPending || !effectiveSource}
              title="Subjekt zentrieren (transparenter Hintergrund)"
            >
              ⊡ Zentrieren
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => padSquareMutation.mutate()}
              disabled={isPending || !effectiveSource}
              title="Quadratisch mit weißem Rand"
            >
              □ Quadratisch
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => resize512Mutation.mutate()}
              disabled={isPending || !effectiveSource}
              title="Auf 512×512 skalieren"
            >
              ↕ 512×512
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => resize1024Mutation.mutate()}
              disabled={isPending || !effectiveSource}
              title="Auf 1024×1024 skalieren"
            >
              ↕ 1024×1024
            </button>
          </div>

          <div
            className="image-editor__crop-area"
            ref={containerRef}
            onMouseDown={handleCropMouseDown}
            onMouseMove={handleCropMouseMove}
            onMouseUp={handleCropMouseUp}
            onMouseLeave={handleCropMouseUp}
          >
            <div className="image-editor__crop-wrapper">
              <img
                ref={imgRef}
                src={previewUrl}
                alt="Vorschau"
                className="image-editor__preview-img"
                onLoad={handleImageLoad}
                draggable={false}
                style={{ maxWidth: "100%", maxHeight: 400, display: "block" }}
              />
              {imageSize.width > 0 &&
                imageSize.height > 0 &&
                cropCoords.width > 0 &&
                cropCoords.height > 0 && (
                  <div
                    className="image-editor__crop-overlay"
                    style={{
                      left: `${(cropCoords.x / imageSize.width) * 100}%`,
                      top: `${(cropCoords.y / imageSize.height) * 100}%`,
                      width: `${(cropCoords.width / imageSize.width) * 100}%`,
                      height: `${(cropCoords.height / imageSize.height) * 100}%`,
                    }}
                  />
                )}
            </div>
          </div>

          <div className="image-editor__crop-coords">
            x: {cropCoords.x} y: {cropCoords.y} w: {cropCoords.width} h:{" "}
            {cropCoords.height}
          </div>
          <button
            type="button"
            className="btn btn--sm"
            onClick={handleCropSubmit}
            disabled={
              isPending ||
              cropCoords.width < 1 ||
              cropCoords.height < 1 ||
              !effectiveSource
            }
          >
            Zuschneiden
          </button>

          {lastEditedUrl && (
            <div className="image-editor__primary-cta">
              <button
                type="button"
                className="btn btn--outline"
                onClick={() => onUseForMesh(lastEditedUrl)}
              >
                → Als Mesh-Input verwenden
              </button>
            </div>
          )}

          <div className="image-editor__resize form-group">
            <h3>Skalieren</h3>
            <div className="image-editor__resize-row">
              <label>
                Breite:
                <input
                  type="number"
                  min={1}
                  value={resizeWidth}
                  onChange={(e) =>
                    setResizeWidth(parseInt(e.target.value, 10) || 512)
                  }
                />
              </label>
              <label>
                Höhe:
                <input
                  type="number"
                  min={1}
                  value={resizeHeight}
                  onChange={(e) =>
                    setResizeHeight(parseInt(e.target.value, 10) || 512)
                  }
                />
              </label>
              <label className="image-editor__checkbox">
                <input
                  type="checkbox"
                  checked={maintainAspect}
                  onChange={(e) => setMaintainAspect(e.target.checked)}
                />
                Seitenverhältnis beibehalten
              </label>
            </div>
            <button
              type="button"
              className="btn btn--sm"
              onClick={() => resizeMutation.mutate()}
              disabled={isPending || !effectiveSource}
            >
              Skalieren
            </button>
          </div>
        </>
      )}

      {allImageFiles.length > 0 && (
        <div className="image-editor__results">
          <h3>Ergebnisse</h3>
          <ul className="image-editor__results-list">
            {allImageFiles.map((filename) => (
              <li key={filename} className="image-editor__result-item">
                <img
                  src={getAssetFileUrl(assetId, filename)}
                  alt={filename}
                  className="image-editor__result-thumb"
                />
                <span className="image-editor__result-name">{filename}</span>
                <button
                  type="button"
                  className="btn btn--sm btn--ghost"
                  onClick={() =>
                    onUseForMesh(getAssetFileUrl(assetId, filename))
                  }
                >
                  → Als Mesh-Input verwenden
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

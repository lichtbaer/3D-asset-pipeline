import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getAssetFileUrl, deleteAssetFile } from "../../api/assets.js";
import type { ImageProcessingEntry } from "../../api/assets.js";

interface ImageProcessingListProps {
  assetId: string;
  imageProcessing: ImageProcessingEntry[];
}

export function ImageProcessingList({
  assetId,
  imageProcessing,
}: ImageProcessingListProps) {
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => deleteAssetFile(assetId, filename),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      queryClient.invalidateQueries({ queryKey: ["image-sources", assetId] });
      setConfirmDelete(null);
    },
  });

  const uniqueOutputs = [
    ...new Set(
      imageProcessing
        .map((e) => e.output_file)
        .filter((f): f is string => !!f)
    ),
  ];

  if (uniqueOutputs.length === 0) return null;

  return (
    <div className="image-processing-list">
      <h4>Bild-Nachbearbeitung</h4>
      <ul className="image-processing-list__items">
        {uniqueOutputs.map((filename) => {
          const url = getAssetFileUrl(assetId, filename);
          const isConfirming = confirmDelete === filename;
          return (
            <li key={filename} className="image-processing-list__item">
              <img
                src={url}
                alt={filename}
                className="image-processing-list__thumb"
              />
              <span className="image-processing-list__name">{filename}</span>
              <a href={url} download className="asset-modal__download">
                Download
              </a>
              {isConfirming ? (
                <span className="image-processing-list__delete-confirm">
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
                  className="btn btn--ghost btn--sm image-processing-list__delete-btn"
                  onClick={() => setConfirmDelete(filename)}
                  aria-label={`${filename} löschen`}
                  title={`${filename} löschen`}
                >
                  🗑
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

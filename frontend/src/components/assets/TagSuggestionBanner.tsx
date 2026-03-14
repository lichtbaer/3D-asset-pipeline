import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { suggestTags } from "../../api/taggingAgent.js";
import { patchAssetMeta } from "../../api/assets.js";

export interface TagSuggestionBannerProps {
  assetId: string;
  includeImageAnalysis?: boolean;
  /** Wenn gesetzt, wird nur bei enabled=true gefetcht (manueller Modus). */
  enabled?: boolean;
  onAccept?: () => void;
  onDismiss?: () => void;
  onAssetUpdate?: () => void;
}

export function TagSuggestionBanner({
  assetId,
  includeImageAnalysis = false,
  enabled: enabledProp,
  onAccept,
  onDismiss,
  onAssetUpdate,
}: TagSuggestionBannerProps) {
  const queryClient = useQueryClient();
  const [dismissed, setDismissed] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[] | null>(null);

  const isAutoMode = enabledProp === undefined;
  const enabled =
    isAutoMode ? !!assetId && !dismissed : !!assetId && !!enabledProp && !dismissed;

  const { data: suggestion, isLoading, error } = useQuery({
    queryKey: ["tag-suggest", assetId, includeImageAnalysis],
    queryFn: () =>
      suggestTags({
        asset_id: assetId,
        include_image_analysis: includeImageAnalysis,
      }),
    enabled,
  });

  const acceptMutation = useMutation({
    mutationFn: (tags: string[]) => patchAssetMeta(assetId, { tags }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["asset", assetId] });
      void queryClient.invalidateQueries({ queryKey: ["assets"] });
      onAccept?.();
      onAssetUpdate?.();
      setDismissed(true);
    },
  });

  const tags = selectedTags ?? suggestion?.tags ?? [];
  const hasTags = tags.length > 0;

  if (dismissed || !assetId) return null;
  if (isLoading) {
    return (
      <div className="tag-suggestion-banner tag-suggestion-banner--loading">
        <span>🏷 Tag-Vorschläge werden geladen...</span>
      </div>
    );
  }
  if (error || !suggestion) {
    return null;
  }

  const handleRemoveTag = (tag: string) => {
    setSelectedTags((prev) => {
      const next = prev ?? [...suggestion.tags];
      return next.filter((t) => t !== tag);
    });
  };

  const handleAcceptAll = () => {
    if (tags.length > 0) {
      acceptMutation.mutate(tags);
    } else {
      setDismissed(true);
      onDismiss?.();
    }
  };

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  return (
    <div className="tag-suggestion-banner">
      <span className="tag-suggestion-banner__label">🏷 Tag-Vorschläge:</span>
      <div className="tag-suggestion-banner__chips">
        {tags.map((t) => (
          <span key={t} className="tag-suggestion-banner__chip">
            {t}{" "}
            <button
              type="button"
              onClick={() => handleRemoveTag(t)}
              aria-label={`Tag ${t} entfernen`}
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div className="tag-suggestion-banner__actions">
        <button
          type="button"
          className="btn btn--primary btn--sm"
          onClick={handleAcceptAll}
          disabled={!hasTags || acceptMutation.isPending}
        >
          {acceptMutation.isPending ? "..." : "Alle übernehmen"}
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={handleDismiss}
        >
          Ignorieren
        </button>
      </div>
    </div>
  );
}

import { type QueryClient } from "@tanstack/react-query";
import { TagSuggestionBanner } from "./TagSuggestionBanner.js";
import { type AssetDetail } from "../../api/assets.js";

export interface AssetVerwaltungProps {
  data: AssetDetail;
  currentTags: string[];
  allTags: { tags: string[] } | undefined;
  nameInput: string;
  setNameInput: (v: string) => void;
  notesInput: string;
  setNotesInput: (v: string) => void;
  saveMeta: (updates: {
    name?: string | null;
    tags?: string[];
    rating?: number | null;
    notes?: string | null;
    favorited?: boolean | null;
  }) => Promise<void>;
  addTag: (tag: string) => void;
  removeTag: (tag: string) => void;
  tagInput: string;
  setTagInput: (v: string) => void;
  showTagSuggestions: boolean;
  setShowTagSuggestions: (v: boolean) => void;
  tagSuggestions: string[];
  showAiTagSuggestions: boolean;
  setShowAiTagSuggestions: (v: boolean | ((prev: boolean) => boolean)) => void;
  assetId: string;
  onAssetUpdate?: () => void;
  queryClient: QueryClient;
}

export function AssetVerwaltung({
  data,
  currentTags,
  nameInput,
  setNameInput,
  notesInput,
  setNotesInput,
  saveMeta,
  addTag,
  removeTag,
  tagInput,
  setTagInput,
  showTagSuggestions,
  setShowTagSuggestions,
  tagSuggestions,
  showAiTagSuggestions,
  setShowAiTagSuggestions,
  assetId,
  onAssetUpdate,
  queryClient,
}: AssetVerwaltungProps) {
  return (
    <section className="asset-modal__verwaltung">
      <h3>Verwaltung</h3>
      <div className="asset-modal__verwaltung-name">
        <label className="asset-modal__verwaltung-label" htmlFor="asset-name">
          Name:
        </label>
        <input
          id="asset-name"
          type="text"
          className="asset-modal__name-input"
          placeholder="Asset-Name..."
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
          onBlur={(e) => {
            const v = e.target.value.trim() || null;
            void saveMeta({ name: v });
          }}
        />
      </div>
      <div className="asset-modal__verwaltung-tags">
        <label className="asset-modal__verwaltung-label">Tags:</label>
        <div className="asset-modal__tag-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setShowAiTagSuggestions((v: boolean) => !v)}
            aria-pressed={showAiTagSuggestions}
          >
            🤖 Tags vorschlagen
          </button>
        </div>
        {showAiTagSuggestions && (
          <TagSuggestionBanner
            assetId={assetId}
            includeImageAnalysis={true}
            enabled={showAiTagSuggestions}
            onAssetUpdate={() => {
              void queryClient.invalidateQueries({
                queryKey: ["asset", assetId],
              });
              onAssetUpdate?.();
            }}
            onDismiss={() => setShowAiTagSuggestions(false)}
          />
        )}
        <div className="asset-modal__tag-chips">
          {currentTags.map((t) => (
            <span key={t} className="asset-modal__tag-chip">
              {t}{" "}
              <button
                type="button"
                onClick={() => removeTag(t)}
                aria-label={`Tag ${t} entfernen`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <div className="asset-modal__tag-input-wrap">
          <input
            type="text"
            className="asset-modal__tag-input"
            placeholder="+ Tag eingeben..."
            value={tagInput}
            onChange={(e) => {
              setTagInput(e.target.value);
              setShowTagSuggestions(true);
            }}
            onFocus={() => setShowTagSuggestions(true)}
            onBlur={() =>
              setTimeout(() => setShowTagSuggestions(false), 150)
            }
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const v = tagInput.trim();
                if (v) addTag(v);
                else if (tagSuggestions[0]) addTag(tagSuggestions[0]);
              }
            }}
          />
          {showTagSuggestions && tagSuggestions.length > 0 && (
            <ul className="asset-modal__tag-suggestions">
              {tagSuggestions.slice(0, 8).map((t) => (
                <li key={t}>
                  <button
                    type="button"
                    onClick={() => addTag(t)}
                  >
                    {t}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="asset-modal__verwaltung-rating">
        <label className="asset-modal__verwaltung-label">Rating:</label>
        <span className="asset-modal__stars">
          {[1, 2, 3, 4, 5].map((i) => (
            <button
              key={i}
              type="button"
              className="asset-modal__star"
              onClick={() => void saveMeta({ rating: i })}
              aria-label={`${i} Sterne`}
            >
              {i <= (data.rating ?? 0) ? "★" : "☆"}
            </button>
          ))}
        </span>
      </div>
      <div className="asset-modal__verwaltung-notes">
        <label className="asset-modal__verwaltung-label" htmlFor="asset-notes">
          Notiz:
        </label>
        <textarea
          id="asset-notes"
          className="asset-modal__notes-input"
          placeholder="Notizen zum Asset..."
          value={notesInput}
          onChange={(e) => setNotesInput(e.target.value)}
          onBlur={(e) => {
            const v = e.target.value.trim();
            void saveMeta({ notes: v || null });
          }}
        />
      </div>
      <div className="asset-modal__verwaltung-favorit">
        <button
          type="button"
          className={`asset-modal__favorit-btn ${
            data.favorited ? "asset-modal__favorit-btn--on" : ""
          }`}
          onClick={() =>
            void saveMeta({ favorited: !(data.favorited ?? false) })
          }
        >
          {data.favorited ? "♥ Als Favorit markiert" : "♡ Als Favorit markieren"}
        </button>
      </div>
    </section>
  );
}

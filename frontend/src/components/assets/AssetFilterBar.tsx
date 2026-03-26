import type { ListAssetsParams } from "../../api/assets.js";

const SORT_OPTIONS: { value: ListAssetsParams["sort"]; label: string }[] = [
  { value: "created_desc", label: "Neueste" },
  { value: "created_asc", label: "Älteste" },
  { value: "name", label: "Name" },
  { value: "rating", label: "Rating" },
];

const STEP_OPTIONS: { value: ListAssetsParams["has_step"]; label: string }[] = [
  { value: undefined, label: "Alle" },
  { value: "image", label: "Bild" },
  { value: "mesh", label: "Mesh" },
  { value: "rigging", label: "Rig" },
  { value: "animation", label: "Animation" },
];

export interface AssetFilterBarProps {
  searchInput: string;
  setSearchInput: (v: string) => void;
  filterFavorited: boolean | undefined;
  setFilterFavorited: (v: boolean | undefined | ((prev: boolean | undefined) => boolean | undefined)) => void;
  filterStep: ListAssetsParams["has_step"];
  setFilterStep: (v: ListAssetsParams["has_step"]) => void;
  filterSort: ListAssetsParams["sort"];
  setFilterSort: (v: ListAssetsParams["sort"]) => void;
  showFilterDropdown: boolean;
  setShowFilterDropdown: (v: boolean | ((prev: boolean) => boolean)) => void;
  filterTags: string[];
  filterTagInput: string;
  setFilterTagInput: (v: string) => void;
  addFilterTag: (tag: string) => void;
  removeFilterTag: (tag: string) => void;
  hasActiveFilters: boolean;
  clearAllFilters: () => void;
}

export function AssetFilterBar({
  searchInput,
  setSearchInput,
  filterFavorited,
  setFilterFavorited,
  filterStep,
  setFilterStep,
  filterSort,
  setFilterSort,
  showFilterDropdown,
  setShowFilterDropdown,
  filterTags,
  filterTagInput,
  setFilterTagInput,
  addFilterTag,
  removeFilterTag,
  hasActiveFilters,
  clearAllFilters,
}: AssetFilterBarProps) {
  return (
    <>
      <div className="asset-library__search-row">
        <div className="asset-library__search-wrap">
          <span className="asset-library__search-icon" aria-hidden>
            🔍
          </span>
          <input
            type="search"
            className="asset-library__search-input"
            placeholder="Assets suchen (Name, Prompt, Tags)..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            aria-label="Assets suchen"
          />
        </div>
        <button
          type="button"
          className={`btn btn--outline asset-library__favoriten-btn ${
            filterFavorited ? "btn--active" : ""
          }`}
          onClick={() => setFilterFavorited((v) => (v ? undefined : true))}
          aria-pressed={filterFavorited ?? false}
        >
          ☆ Favoriten
        </button>
        <div className="asset-library__filter-dropdown">
          <button
            type="button"
            className="btn btn--outline"
            onClick={() => setShowFilterDropdown((v) => !v)}
            aria-expanded={showFilterDropdown}
            aria-haspopup="true"
          >
            Filter ▾
          </button>
          {showFilterDropdown && (
            <div className="asset-library__filter-panel">
              <div className="asset-library__filter-group">
                <label className="asset-library__filter-label">Step:</label>
                <select
                  value={filterStep ?? ""}
                  onChange={(e) =>
                    setFilterStep(
                      (e.target.value || undefined) as ListAssetsParams["has_step"]
                    )
                  }
                >
                  {STEP_OPTIONS.map((o) => (
                    <option key={o.value ?? "all"} value={o.value ?? ""}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="asset-library__filter-group">
                <label className="asset-library__filter-label">Sort:</label>
                <select
                  value={filterSort}
                  onChange={(e) =>
                    setFilterSort(e.target.value as ListAssetsParams["sort"])
                  }
                >
                  {SORT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      </div>

      {hasActiveFilters && (
        <div className="asset-library__filter-chips">
          {filterTags.map((t) => (
            <span key={t} className="asset-library__chip">
              {t}{" "}
              <button
                type="button"
                onClick={() => removeFilterTag(t)}
                aria-label={`Tag ${t} entfernen`}
              >
                ×
              </button>
            </span>
          ))}
          <div className="asset-library__chip-input-wrap">
            <input
              type="text"
              className="asset-library__chip-input"
              placeholder="+ Tag hinzufügen"
              value={filterTagInput}
              onChange={(e) => setFilterTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  addFilterTag(filterTagInput);
                }
              }}
            />
          </div>
          <button
            type="button"
            className="asset-library__clear-filters"
            onClick={clearAllFilters}
          >
            Alle Filter löschen
          </button>
        </div>
      )}
    </>
  );
}

import { useState } from 'react';
import LessonCard from './LessonCard.jsx';
import LessonThemes from './LessonThemes.jsx';
import WordcloudDialog from './WordcloudDialog.jsx';

function SearchIcon() {
  return (
    <svg className="search-input-wrap__icon" width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
      />
    </svg>
  );
}

const SORT_OPTIONS = [
  { id: 'newest', label: 'Newest' },
  { id: 'oldest', label: 'Oldest' },
  { id: 'az', label: 'A–Z' },
];

export default function LessonLibrary({
  searchInput,
  searchPending,
  onSearchChange,
  onSearchKeyDown,
  onClearSearch,
  filteredLessons,
  totalLessonCount,
  filterActive,
  visibleClusters,
  selectedThemeIds,
  selectedThemeLabels,
  onThemeToggle,
  sortKey,
  onSortChange,
  onResetFilters,
  hasActiveFilters,
  themesVisible,
  onToggleThemes,
}) {
  const showClear = searchInput.length > 0;
  const [wcModal, setWcModal] = useState(null);

  const shown = filteredLessons.length;
  const total = totalLessonCount;

  return (
    <section
      className="library library-panel panel-card"
      aria-labelledby="lesson-library-heading"
    >
      <div className="panel-card__titlebar">
        <h2 id="lesson-library-heading" className="section-title">
          Lesson Library
        </h2>
        <p className="panel-helper">Search micro-lessons and filter by theme.</p>
        {hasActiveFilters ? (
          <div className="filter-bar" role="status" aria-live="polite">
            {selectedThemeIds.length > 0 ? (
              <span className="filter-chip">
                Themes:{' '}
                <strong>
                  {selectedThemeLabels.map((name, i) => (
                    <span key={selectedThemeIds[i]}>
                      {i > 0 ? ', ' : ''}
                      {name}
                    </span>
                  ))}
                </strong>
              </span>
            ) : null}
            {selectedThemeIds.length > 0 && searchInput.trim() ? (
              <span className="filter-bar__sep" aria-hidden="true">
                {' '}
                ·{' '}
              </span>
            ) : null}
            {searchInput.trim() ? (
              <span className="filter-chip filter-chip--muted">Search: &ldquo;{searchInput.trim()}&rdquo;</span>
            ) : null}
            <button type="button" className="btn-reset" onClick={onResetFilters}>
              Reset filters
            </button>
          </div>
        ) : null}
      </div>

      <div role="search" className="search-panel search-panel--dominant">
        <label htmlFor="lesson-search" className="visually-hidden">
          Search micro-lessons by title or topic
        </label>
        <div className="search-input-wrap search-input-wrap--dominant">
          <SearchIcon />
          <input
            type="search"
            id="lesson-search"
            className="search-input-wrap__input"
            placeholder="Search micro-lessons by title or topic"
            autoComplete="off"
            aria-label="Search micro-lessons by title or topic"
            value={searchInput}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={onSearchKeyDown}
          />
          {showClear ? (
            <button
              type="button"
              className="search-input-wrap__clear"
              onClick={onClearSearch}
              aria-label="Clear search"
            >
              ×
            </button>
          ) : null}
        </div>
      </div>

      <div className="library-toolbar">
        <p className="library-toolbar__counts" role="status" aria-live="polite">
          {searchPending ? (
            <span className="library-toolbar__pending">Updating results…</span>
          ) : filterActive ? (
            <>
              <strong className="library-toolbar__num">{shown}</strong>
              <span className="library-toolbar__of"> of {total} lessons</span>
              {shown < total ? <span className="library-toolbar__hint"> match</span> : null}
            </>
          ) : (
            <>
              <strong className="library-toolbar__num">{shown}</strong>
              <span className="library-toolbar__of"> lessons</span>
            </>
          )}
        </p>
        <div className="library-toolbar__end">
          <button
            type="button"
            className={`themes-toggle${themesVisible ? ' themes-toggle--active' : ''}`}
            aria-expanded={themesVisible}
            onClick={onToggleThemes}
          >
            Themes
          </button>
          <div className="sort-toolbar" role="toolbar" aria-label="Sort lesson list">
            <span className="sort-toolbar__label" id="sort-label">
              Sort
            </span>
            <div className="sort-toolbar__buttons" role="group" aria-labelledby="sort-label">
              {SORT_OPTIONS.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  className={`sort-pill${sortKey === id ? ' sort-pill--active' : ''}`}
                  aria-pressed={sortKey === id}
                  onClick={() => onSortChange(id)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {themesVisible ? (
        <div id="lesson-themes-region">
          <LessonThemes
            visibleClusters={visibleClusters}
            selectedThemeIds={selectedThemeIds}
            onThemeToggle={onThemeToggle}
          />
        </div>
      ) : null}

      {filteredLessons.length === 0 ? (
        <p className="lesson-list-empty" role="status">
          No lessons match your filters.
        </p>
      ) : (
        <ul className="lesson-list" role="list">
          {filteredLessons.map((L) => (
            <li key={L.transcript_id} className="lesson-list__item" role="listitem">
              <LessonCard L={L} onOpenWordcloudModal={setWcModal} />
            </li>
          ))}
        </ul>
      )}

      <WordcloudDialog payload={wcModal} onClose={() => setWcModal(null)} />
    </section>
  );
}

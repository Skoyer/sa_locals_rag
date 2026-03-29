import { videoDisplayTitle, videoTooltipText } from '../normalize.js';

function SearchIcon() {
  return (
    <svg className="search-input-wrap__icon" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
      />
    </svg>
  );
}

export default function LessonLibrary({
  searchInput,
  onSearchChange,
  onSearchKeyDown,
  onClearSearch,
  filteredLessons,
  activeThemeId,
  activeThemeName,
  onResetFilters,
  hasActiveFilters,
}) {
  const showClear = searchInput.length > 0;

  return (
    <section className="library panel-card" aria-labelledby="lesson-library-heading">
      <div className="panel-card__titlebar">
        <h2 id="lesson-library-heading" className="section-title">
          Lesson Library
        </h2>
        <p className="panel-helper">Search and skim all micro-lessons.</p>
        {hasActiveFilters ? (
          <div className="filter-bar" role="status" aria-live="polite">
            {activeThemeId != null ? (
              <span className="filter-chip">
                Theme: <strong>{activeThemeName || `Cluster #${activeThemeId}`}</strong>
              </span>
            ) : null}
            {activeThemeId != null && searchInput.trim() ? (
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

      <div role="search" className="search-panel">
        <label htmlFor="lesson-search" className="visually-hidden">
          Search lessons by title or description
        </label>
        <div className="search-input-wrap">
          <SearchIcon />
          <input
            type="search"
            id="lesson-search"
            className="search-input-wrap__input"
            placeholder="Search by title or description…"
            autoComplete="off"
            aria-label="Search lessons by title or description"
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

      {filteredLessons.length === 0 ? (
        <p className="lesson-list-empty" role="status">
          No lessons match your filters.
        </p>
      ) : (
      <ul className="lesson-list" role="list">
        {filteredLessons.map((L) => {
          const title = videoDisplayTitle(L);
          const tip = videoTooltipText(L);
          const excerpt = (L.short_description || L.summary_text || L.core_lesson || '').trim();
          const themeTag = L.primary_topics?.[0] || L.cluster_name || '';
          const href = L.url || '#';
          const rowContent = (
            <>
              <span className="lesson-row__title">{title}</span>
              {excerpt ? (
                <span className="lesson-row__excerpt">{excerpt}</span>
              ) : null}
              <span className="lesson-row__meta">
                #{L.transcript_id}
                {themeTag ? ` · ${themeTag}` : ''}
              </span>
            </>
          );
          return (
            <li key={L.transcript_id} className="lesson-list__item" role="listitem">
              {L.url ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="lesson-row"
                  title={tip}
                >
                  {rowContent}
                </a>
              ) : (
                <div className="lesson-row lesson-row--static">{rowContent}</div>
              )}
            </li>
          );
        })}
      </ul>
      )}
    </section>
  );
}

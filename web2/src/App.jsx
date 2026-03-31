import { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';
import PageHeader from './components/PageHeader.jsx';
import HeroWordCloud from './components/HeroWordCloud.jsx';
import LessonLibrary from './components/LessonLibrary.jsx';
import { useDebouncedValue } from './hooks/useDebouncedValue.js';
import {
  clusterRowLabel,
  clusterThemeAbbrev,
  lessonMatchesFilters,
  sortLessons,
  themeTitleMatchesQuery,
} from './normalize.js';

function getData() {
  return window.SA_LESSONS_DATA;
}

function buildClusters(lessons) {
  const byCluster = {};
  (lessons || []).forEach((L) => {
    const c = L.cluster_id;
    if (c == null) return;
    if (!byCluster[c]) byCluster[c] = [];
    byCluster[c].push(L);
  });
  return Object.keys(byCluster)
    .sort((a, b) => +a - +b)
    .map((cid) => ({
      cid,
      list: byCluster[cid].sort((a, b) => (a.title || '').localeCompare(b.title || '')),
    }));
}

export default function App() {
  const data = getData();
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebouncedValue(searchInput, 250);
  const [filterQuery, setFilterQuery] = useState('');
  const [selectedThemeIds, setSelectedThemeIds] = useState([]);
  const [sortKey, setSortKey] = useState('newest');
  const [themesVisible, setThemesVisible] = useState(true);

  useEffect(() => {
    setFilterQuery(debouncedSearch.trim().toLowerCase());
  }, [debouncedSearch]);

  const lessons = useMemo(() => data?.lessons ?? [], [data]);
  const stats = data?.stats || {};

  const clusters = useMemo(() => buildClusters(lessons), [lessons]);

  const visibleClusters = useMemo(() => {
    return clusters.filter((row) => {
      const label = clusterRowLabel(row) || `Theme ${clusterThemeAbbrev(row.cid)}`;
      return themeTitleMatchesQuery(filterQuery, label);
    });
  }, [clusters, filterQuery]);

  useEffect(() => {
    const visible = new Set(visibleClusters.map((c) => String(c.cid)));
    setSelectedThemeIds((prev) => prev.filter((id) => visible.has(id)));
  }, [visibleClusters]);

  const filteredLessons = useMemo(() => {
    const matched = lessons.filter((L) =>
      lessonMatchesFilters(L, filterQuery, selectedThemeIds),
    );
    return sortLessons(matched, sortKey);
  }, [lessons, filterQuery, selectedThemeIds, sortKey]);

  const selectedThemeLabels = useMemo(() => {
    return selectedThemeIds.map((id) => {
      const row = clusters.find((c) => String(c.cid) === id);
      if (!row) return `Theme ${id}`;
      return clusterRowLabel(row) || `Theme ${clusterThemeAbbrev(id)}`;
    });
  }, [selectedThemeIds, clusters]);

  const hasActiveFilters = selectedThemeIds.length > 0 || searchInput.trim() !== '';

  const searchPending =
    searchInput.trim() !== debouncedSearch.trim();

  const handleSearchKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        setFilterQuery(searchInput.trim().toLowerCase());
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setSearchInput('');
        setFilterQuery('');
      }
    },
    [searchInput],
  );

  const onClearSearch = useCallback(() => {
    setSearchInput('');
    setFilterQuery('');
  }, []);

  const onResetFilters = useCallback(() => {
    setSearchInput('');
    setFilterQuery('');
    setSelectedThemeIds([]);
  }, []);

  const onThemeToggle = useCallback((cid) => {
    const s = String(cid);
    setSelectedThemeIds((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s],
    );
  }, []);

  if (!data) {
    return (
      <p style={{ padding: '2rem' }}>
        Missing data: ensure <code>public/data.js</code> is present and defines{' '}
        <code>window.SA_LESSONS_DATA</code>.
      </p>
    );
  }

  return (
    <>
      <PageHeader />
      <main>
        <HeroWordCloud />
        <section className="content-band" aria-label="Library and themes">
          <div className="page-shell page-shell--band page-shell--library-full">
            <LessonLibrary
              searchInput={searchInput}
              searchPending={searchPending}
              onSearchChange={setSearchInput}
              onSearchKeyDown={handleSearchKeyDown}
              onClearSearch={onClearSearch}
              filteredLessons={filteredLessons}
              totalLessonCount={lessons.length}
              filterActive={Boolean(filterQuery) || selectedThemeIds.length > 0}
              visibleClusters={visibleClusters}
              selectedThemeIds={selectedThemeIds}
              selectedThemeLabels={selectedThemeLabels}
              onThemeToggle={onThemeToggle}
              sortKey={sortKey}
              onSortChange={setSortKey}
              onResetFilters={onResetFilters}
              hasActiveFilters={hasActiveFilters}
              themesVisible={themesVisible}
              onToggleThemes={() => setThemesVisible((v) => !v)}
            />
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="page-shell">
          <div className="site-footer__stats">
            Videos: {stats.total_videos ?? 0} &nbsp; Themes: {stats.total_clusters ?? 0} &nbsp; Topic
            tags: {stats.topics ?? 0}
          </div>
          <div className="site-footer__gen">Generated: {data.generated_at || ''} — static export</div>
        </div>
      </footer>
    </>
  );
}

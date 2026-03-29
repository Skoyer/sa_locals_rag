import { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';
import PageHeader from './components/PageHeader.jsx';
import HeroWordCloud from './components/HeroWordCloud.jsx';
import LessonLibrary from './components/LessonLibrary.jsx';
import LessonThemes from './components/LessonThemes.jsx';
import { useDebouncedValue } from './hooks/useDebouncedValue.js';
import {
  clusterDisplayTitle,
  lessonMatchesFilters,
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
  const [activeThemeId, setActiveThemeId] = useState(null);

  useEffect(() => {
    setFilterQuery(debouncedSearch.trim().toLowerCase());
  }, [debouncedSearch]);

  const lessons = useMemo(() => data?.lessons ?? [], [data]);
  const stats = data?.stats || {};

  const clusters = useMemo(() => buildClusters(lessons), [lessons]);

  const filteredLessons = useMemo(() => {
    return lessons.filter((L) => lessonMatchesFilters(L, filterQuery, activeThemeId));
  }, [lessons, filterQuery, activeThemeId]);

  const activeThemeName = useMemo(() => {
    if (activeThemeId == null) return '';
    const row = clusters.find((c) => String(c.cid) === String(activeThemeId));
    if (!row) return '';
    const first = row.list[0] || {};
    return clusterDisplayTitle({
      title2: first.title2,
      title_original: first.cluster_name,
      cluster_name: first.cluster_name,
    });
  }, [activeThemeId, clusters]);

  const hasActiveFilters =
    activeThemeId != null || searchInput.trim() !== '';

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
    setActiveThemeId(null);
  }, []);

  const onThemeSelect = useCallback((cid) => {
    setActiveThemeId((prev) => (String(prev) === String(cid) ? null : cid));
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
          <div className="page-shell page-shell--band">
            <LessonLibrary
              searchInput={searchInput}
              onSearchChange={setSearchInput}
              onSearchKeyDown={handleSearchKeyDown}
              onClearSearch={onClearSearch}
              filteredLessons={filteredLessons}
              activeThemeId={activeThemeId}
              activeThemeName={activeThemeName}
              onResetFilters={onResetFilters}
              hasActiveFilters={hasActiveFilters}
            />
            <LessonThemes
              clusters={clusters}
              activeThemeId={activeThemeId}
              onThemeSelect={onThemeSelect}
            />
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="page-shell">
          <div className="site-footer__stats">
            Videos: {stats.total_videos ?? 0} &nbsp; Clusters: {stats.total_clusters ?? 0} &nbsp; Topic
            tags: {stats.topics ?? 0}
          </div>
          <div className="site-footer__gen">Generated: {data.generated_at || ''} — static export</div>
        </div>
      </footer>
    </>
  );
}

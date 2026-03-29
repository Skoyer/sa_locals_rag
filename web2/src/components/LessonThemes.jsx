import { clusterDisplayTitle, clusterThemeAbbrev } from '../normalize.js';

export default function LessonThemes({ clusters, activeThemeId, onThemeSelect }) {
  return (
    <section className="themes panel-card" aria-labelledby="lesson-themes-heading">
      <div className="panel-card__titlebar">
        <h2 id="lesson-themes-heading" className="section-title">
          Lesson Themes
        </h2>
        <p className="panel-helper">Explore lessons grouped by theme.</p>
      </div>
      <div className="theme-grid">
        {clusters.map(({ cid, list }) => {
          const first = list[0] || {};
          const name = clusterDisplayTitle({
            title2: first.title2,
            title_original: first.cluster_name,
            cluster_name: first.cluster_name,
          });
          const abbrev = clusterThemeAbbrev(cid);
          const label = name || `Theme ${abbrev}`;
          const isActive = String(activeThemeId) === String(cid);
          return (
            <button
              key={cid}
              type="button"
              className={`theme-card${isActive ? ' theme-card--active' : ''}`}
              onClick={() => onThemeSelect(cid)}
              aria-pressed={isActive}
              aria-label={`Filter library by theme: ${label}. ${list.length} lessons.`}
            >
              <img
                className="theme-card__thumb"
                src={`/wordclouds/clusters/cluster_${cid}.png`}
                alt=""
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
              <span className="theme-card__title">{label}</span>
              <span className="theme-card__meta">
                Theme {abbrev} · {list.length} lesson{list.length === 1 ? '' : 's'}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

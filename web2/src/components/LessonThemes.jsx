import { clusterRowLabel, clusterThemeAbbrev } from '../normalize.js';

export default function LessonThemes({ visibleClusters, selectedThemeIds, onThemeToggle }) {
  if (!visibleClusters.length) {
    return (
      <div className="theme-pills-empty" role="status">
        No themes match the current search. Clear or change the search to see all themes.
      </div>
    );
  }

  return (
    <div className="theme-pills-wrap">
      <h3 className="theme-pills-heading">Lesson themes</h3>
      <div className="theme-pills" role="group" aria-label="Filter by lesson theme">
        {visibleClusters.map(({ cid, list }) => {
          const label = clusterRowLabel({ cid, list }) || `Theme ${clusterThemeAbbrev(cid)}`;
          const isOn = selectedThemeIds.includes(String(cid));
          return (
            <button
              key={cid}
              type="button"
              className={`theme-pill${isOn ? ' theme-pill--active' : ''}`}
              aria-pressed={isOn}
              onClick={() => onThemeToggle(cid)}
              aria-label={`${isOn ? 'Remove' : 'Add'} filter ${label}, ${list.length} lessons`}
            >
              <span className="theme-pill__label">{label}</span>
              <span className="theme-pill__count">{list.length}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

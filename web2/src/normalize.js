export function normalizeClusterTitle(raw) {
  if (!raw) return '';
  return raw
    .replace(/^Micro Lessons? on\s+/i, '')
    .replace(/^Micro Lessons?\s+for\s+/i, '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
}

export function normalizeVideoTitle(raw, transcriptId) {
  if (!raw && transcriptId == null) return '';
  const rawStr = raw || '';
  const episodeMatch = rawStr.match(/^#(\d+)\s*[—:-]?\s*/);
  const episodeNumber = episodeMatch
    ? episodeMatch[1]
    : transcriptId != null
      ? String(transcriptId)
      : null;
  let title = rawStr.replace(/^#\d+\s*[—:-]?\s*/i, '');
  title = title.replace(/^A Micro Lesson (on|about)\s+/i, '');
  title = title.trim();
  if (!title) title = transcriptId != null ? 'Lesson' : '';
  title = title.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
  if (episodeNumber) {
    return `${title} (#${episodeNumber})`;
  }
  return title;
}

export function clusterDisplayTitle(cluster) {
  if (cluster?.title2) return cluster.title2;
  return normalizeClusterTitle(cluster?.title_original || cluster?.cluster_name || '');
}

/** Short codes for theme footers (aligned to cluster_id in data). */
export const CLUSTER_THEME_ABBREV = {
  0: 'TM',
  1: 'RM',
  2: 'IC',
  3: 'PB',
  4: 'SC',
  5: 'HT',
  6: 'SP',
  7: 'ML',
  8: 'PT',
  9: 'SM',
  10: 'MH',
  11: 'EC',
  12: 'LP',
  13: 'FP',
  14: 'CD',
};

export function clusterThemeAbbrev(cid) {
  const n = Number(cid);
  return Number.isFinite(n) && CLUSTER_THEME_ABBREV[n] != null
    ? CLUSTER_THEME_ABBREV[n]
    : String(cid ?? '');
}

export function videoDisplayTitle(L) {
  if (L.display_title) return L.display_title;
  const raw = L.title_original != null ? L.title_original : L.title;
  return normalizeVideoTitle(raw, L.transcript_id);
}

export function videoTooltipText(L) {
  const d = L.short_description || L.summary_text || L.core_lesson || '';
  return d ? String(d).trim() : 'Micro lesson video';
}

/** Public URL for per-lesson word cloud image (served from /wordclouds/...). */
export function lessonWordcloudSrc(L) {
  const p = (L.wordcloud_path || '').trim();
  if (p) {
    const normalized = p.replace(/^\.\//, '').replace(/\\/g, '/');
    return normalized.startsWith('/') ? normalized : `/${normalized}`;
  }
  if (L.transcript_id != null) {
    return `/wordclouds/per_video/${L.transcript_id}.png`;
  }
  return '';
}

function norm(s) {
  return (s || '').toLowerCase();
}

export function lessonSearchMatches(q, L) {
  if (!q) return true;
  const display = videoDisplayTitle(L);
  const hay = [
    display,
    L.short_description,
    L.summary_text,
    L.core_lesson,
    L.title,
    L.cluster_name,
    ...(L.primary_topics || []),
    ...(L.topic_buckets || []),
    ...(L.key_concepts || []),
  ]
    .filter(Boolean)
    .map(norm)
    .join(' ');
  return q.split(/\s+/).every((t) => !t || hay.includes(t));
}

/** True if normalized theme label matches all whitespace-separated tokens in q. */
export function themeTitleMatchesQuery(q, label) {
  const t = (q || '').trim().toLowerCase();
  if (!t) return true;
  const hay = (label || '').toLowerCase();
  return t.split(/\s+/).every((tok) => !tok || hay.includes(tok));
}

/** Cluster row shape: { cid, list } — derive display label from first lesson. */
export function clusterRowLabel(row) {
  const first = row.list[0] || {};
  return clusterDisplayTitle({
    title2: first.title2,
    title_original: first.cluster_name,
    cluster_name: first.cluster_name,
  });
}

/** Filter by search query and optional multi-select theme ids (OR). Empty selection = no theme filter. */
export function lessonMatchesFilters(L, q, selectedThemeIds) {
  if (selectedThemeIds && selectedThemeIds.length > 0) {
    if (!selectedThemeIds.includes(String(L.cluster_id))) {
      return false;
    }
  }
  return lessonSearchMatches(q, L);
}

export function sortLessons(lessons, sortKey) {
  const copy = [...lessons];
  if (sortKey === 'newest') {
    copy.sort((a, b) => (Number(b.transcript_id) || 0) - (Number(a.transcript_id) || 0));
  } else if (sortKey === 'oldest') {
    copy.sort((a, b) => (Number(a.transcript_id) || 0) - (Number(b.transcript_id) || 0));
  } else {
    copy.sort((a, b) =>
      videoDisplayTitle(a).localeCompare(videoDisplayTitle(b), undefined, { sensitivity: 'base' }),
    );
  }
  return copy;
}

/** Format video length for list meta; empty if unknown. */
export function formatDurationSeconds(sec) {
  if (sec == null || sec === '') return '';
  const n = Number(sec);
  if (!Number.isFinite(n) || n < 0) return '';
  const s = Math.round(n);
  const m = Math.floor(s / 60);
  const r = s % 60;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    const mm = m % 60;
    return `${h}h ${mm}m`;
  }
  return `${m}:${String(r).padStart(2, '0')}`;
}

/** Comma-separated topic tags for meta line (falls back to cluster name). */
export function formatLessonTags(L) {
  const topics = (L.primary_topics || []).filter(Boolean);
  if (topics.length) return topics.slice(0, 4).join(', ');
  return (L.cluster_name || '').trim();
}

/** Ordered meta segments: lesson #, tags, duration — omit empties. */
export function buildLessonMetaSegments(L) {
  const segments = [];
  if (L.transcript_id != null) {
    segments.push(`Lesson ${L.transcript_id}`);
  }
  const tags = formatLessonTags(L);
  if (tags) segments.push(tags);
  const dur = formatDurationSeconds(L.duration_seconds);
  if (dur) segments.push(dur);
  return segments;
}

export function normalizeClusterTitle(raw) {
  if (!raw) return '';
  return raw
    .replace(/^Micro Lessons? on\s+/i, '')
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

export function videoDisplayTitle(L) {
  if (L.display_title) return L.display_title;
  const raw = L.title_original != null ? L.title_original : L.title;
  return normalizeVideoTitle(raw, L.transcript_id);
}

export function videoTooltipText(L) {
  const d = L.short_description || L.summary_text || L.core_lesson || '';
  return d ? String(d).trim() : 'Micro lesson video';
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
    ...(L.key_concepts || []),
  ]
    .filter(Boolean)
    .map(norm)
    .join(' ');
  return q.split(/\s+/).every((t) => !t || hay.includes(t));
}

/** Filter by optional theme (cluster id) and search query. */
export function lessonMatchesFilters(L, q, themeId) {
  if (themeId != null && themeId !== '' && String(L.cluster_id) !== String(themeId)) {
    return false;
  }
  return lessonSearchMatches(q, L);
}

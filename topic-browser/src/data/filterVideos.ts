import type { Video } from '../types'

/** Mirrors legacy `lessonMatches` in `web/index.html` (substring tokens in haystack). */
export function lessonMatchesQuery(q: string, video: Video): boolean {
  const query = q.trim().toLowerCase()
  if (!query) return true
  const hay = [
    video.title,
    video.core_lesson,
    video.summary_text,
    ...(video.key_concepts || []),
    ...video.topics.map((t) => t.name),
    video.cluster?.name ?? '',
  ]
    .join(' ')
    .toLowerCase()
  return query.split(/\s+/).every((t) => !t || hay.includes(t))
}

export function filterVideos(
  videos: Video[],
  selectedTopicId: string | null,
  selectedClusterId: number | null,
  searchQuery: string,
): Video[] {
  return videos.filter((v) => {
    if (selectedTopicId != null) {
      if (!v.topics.some((t) => t.id === selectedTopicId)) return false
    }
    if (selectedClusterId != null) {
      if (v.cluster?.id !== selectedClusterId) return false
    }
    if (!lessonMatchesQuery(searchQuery, v)) return false
    return true
  })
}

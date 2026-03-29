import type { Video } from '../types'

import { videoMatchesInterestBuckets } from './interestBuckets'

/** Mirrors legacy `lessonMatches` in `web/index.html` (substring tokens in haystack). */
export function lessonMatchesQuery(q: string, video: Video): boolean {
  const query = q.trim().toLowerCase()
  if (!query) return true
  const hay = [
    video.title,
    video.core_lesson,
    video.summary_text,
    ...(video.key_concepts || []),
    ...(video.topics ?? []).map((t) => t.name),
    video.cluster?.name ?? '',
  ]
    .join(' ')
    .toLowerCase()
  return query.split(/\s+/).every((t) => !t || hay.includes(t))
}

export function filterVideos(
  videos: Video[],
  selectedTopicIds: string[],
  interestBucketSlugs: string[] | null,
  selectedClusterId: number | null,
  searchQuery: string,
): Video[] {
  return videos.filter((v) => {
    if (interestBucketSlugs && interestBucketSlugs.length > 0) {
      if (!videoMatchesInterestBuckets(v.topic_buckets, interestBucketSlugs))
        return false
    } else if (selectedTopicIds.length > 0) {
      const videoTopicIds = new Set((v.topics ?? []).map((t) => t.id))
      if (!selectedTopicIds.some((id) => videoTopicIds.has(id)))
        return false
    }
    if (selectedClusterId != null) {
      if (v.cluster?.id !== selectedClusterId) return false
    }
    if (!lessonMatchesQuery(searchQuery, v)) return false
    return true
  })
}

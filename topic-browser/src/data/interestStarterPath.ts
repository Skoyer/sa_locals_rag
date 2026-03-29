import type { Video } from '../types'

import { videoMatchesInterestBuckets } from './interestBuckets'

function difficultyRank(d: string): number {
  const x = (d || 'intermediate').toLowerCase()
  if (x === 'beginner') return 0
  if (x === 'advanced') return 2
  return 1
}

/** Order lessons for a starter path: difficulty then transcript id. */
export function sortVideosForInterestPath(videos: Video[]): Video[] {
  return [...videos].sort((a, b) => {
    const dr =
      difficultyRank(a.difficulty || 'intermediate') -
      difficultyRank(b.difficulty || 'intermediate')
    if (dr !== 0) return dr
    return a.id - b.id
  })
}

/** Videos matching interest buckets, ordered for the default starter path. */
export function getInterestStarterVideoIds(
  allVideos: Video[],
  bucketSlugs: string[],
): number[] {
  const matched = allVideos.filter((v) =>
    videoMatchesInterestBuckets(v.topic_buckets, bucketSlugs),
  )
  return sortVideosForInterestPath(matched).map((v) => v.id)
}

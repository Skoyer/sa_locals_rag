import { useDeferredValue, useMemo } from 'react'

import { filterVideos } from '../data/filterVideos'
import { useTopicBrowserStore } from '../store/useTopicBrowserStore'
import type { Video } from '../types'

function intersectWithPathOrder(
  base: Video[],
  pathIds: number[],
): Video[] {
  const order = new Map(pathIds.map((id, i) => [id, i]))
  const allowed = new Set(pathIds)
  return base
    .filter((v) => allowed.has(v.id))
    .sort(
      (a, b) =>
        (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0),
    )
}

export function useFilteredVideos(): Video[] {
  const allVideos = useTopicBrowserStore((s) => s.allVideos)
  const selectedTopicIds = useTopicBrowserStore((s) => s.selectedTopicIds)
  const interestBucketSlugs = useTopicBrowserStore((s) => s.interestBucketSlugs)
  const selectedClusterId = useTopicBrowserStore((s) => s.selectedClusterId)
  const searchQuery = useTopicBrowserStore((s) => s.searchQuery)
  const deferredSearchQuery = useDeferredValue(searchQuery)
  const pathFilterVideoIds = useTopicBrowserStore(
    (s) => s.pathFilterVideoIds,
  )
  const pathPreviewMode = useTopicBrowserStore((s) => s.pathPreviewMode)

  return useMemo(() => {
    const base = filterVideos(
      allVideos,
      selectedTopicIds,
      interestBucketSlugs,
      selectedClusterId,
      deferredSearchQuery,
    )
    if (pathPreviewMode) {
      return base
    }
    if (pathFilterVideoIds && pathFilterVideoIds.length > 0) {
      return intersectWithPathOrder(base, pathFilterVideoIds)
    }
    return base
  }, [
    allVideos,
    selectedTopicIds,
    interestBucketSlugs,
    selectedClusterId,
    deferredSearchQuery,
    pathFilterVideoIds,
    pathPreviewMode,
  ])
}

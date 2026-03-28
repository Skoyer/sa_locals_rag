import { useMemo } from 'react'

import { filterVideos } from '../data/filterVideos'
import { useTopicBrowserStore } from '../store/useTopicBrowserStore'
import type { Video } from '../types'

export function useFilteredVideos(): Video[] {
  const allVideos = useTopicBrowserStore((s) => s.allVideos)
  const selectedTopicId = useTopicBrowserStore((s) => s.selectedTopicId)
  const selectedClusterId = useTopicBrowserStore((s) => s.selectedClusterId)
  const searchQuery = useTopicBrowserStore((s) => s.searchQuery)

  return useMemo(
    () =>
      filterVideos(
        allVideos,
        selectedTopicId,
        selectedClusterId,
        searchQuery,
      ),
    [allVideos, selectedTopicId, selectedClusterId, searchQuery],
  )
}

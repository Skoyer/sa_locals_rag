import { X } from 'lucide-react'

import { useFilteredVideos } from '../../hooks/useFilteredVideos'
import {
  selectSelectedCluster,
  selectSelectedTopic,
  useTopicBrowserStore,
} from '../../store/useTopicBrowserStore'

export function ActiveFiltersBar() {
  const searchQuery = useTopicBrowserStore((s) => s.searchQuery)
  const clearTopic = useTopicBrowserStore((s) => s.clearTopic)
  const clearCluster = useTopicBrowserStore((s) => s.clearCluster)
  const clearSearch = useTopicBrowserStore((s) => s.clearSearch)
  const clearAllFilters = useTopicBrowserStore((s) => s.clearAllFilters)

  const filteredVideos = useFilteredVideos()
  const filteredCount = filteredVideos.length

  const topic = useTopicBrowserStore(selectSelectedTopic)
  const cluster = useTopicBrowserStore(selectSelectedCluster)

  const hasFilters =
    topic != null || cluster != null || searchQuery.trim().length > 0

  const parts: string[] = []
  if (topic) parts.push(topic.name)
  if (cluster) parts.push(cluster.name)
  if (searchQuery.trim()) parts.push(`"${searchQuery.trim()}"`)

  const summary =
    parts.length > 0 ? parts.join(' + ') : 'all videos'

  return (
    <div className="rounded-lg border border-zinc-700/80 bg-zinc-900/50 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-zinc-500">
          Filtered by:
        </span>
        {topic ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-zinc-800 px-2.5 py-1 text-xs text-zinc-200">
            {topic.name}
            <button
              type="button"
              className="rounded p-0.5 hover:bg-zinc-700"
              onClick={clearTopic}
              aria-label={`Remove topic ${topic.name}`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        ) : null}
        {cluster ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-zinc-800 px-2.5 py-1 text-xs text-zinc-200">
            {cluster.name}
            <button
              type="button"
              className="rounded p-0.5 hover:bg-zinc-700"
              onClick={clearCluster}
              aria-label={`Remove cluster ${cluster.name}`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        ) : null}
        {searchQuery.trim() ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-zinc-800 px-2.5 py-1 text-xs text-zinc-200">
            &quot;{searchQuery.trim()}&quot;
            <button
              type="button"
              className="rounded p-0.5 hover:bg-zinc-700"
              onClick={clearSearch}
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        ) : null}
        {!hasFilters ? (
          <span className="text-xs text-zinc-600">(none)</span>
        ) : null}
        {hasFilters ? (
          <button
            type="button"
            className="ml-auto text-xs text-violet-400 hover:text-violet-300"
            onClick={clearAllFilters}
          >
            Clear all
          </button>
        ) : null}
      </div>
      <p className="mt-2 text-sm text-zinc-300">
        Showing{' '}
        <strong className="font-semibold text-zinc-100">{filteredCount}</strong>{' '}
        video{filteredCount === 1 ? '' : 's'}
        {hasFilters ? (
          <>
            {' '}
            for: <span className="text-zinc-400">{summary}</span>
          </>
        ) : null}
      </p>
    </div>
  )
}

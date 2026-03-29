import { X } from 'lucide-react'
import { useMemo } from 'react'

import { useFilteredVideos } from '../../hooks/useFilteredVideos'
import { selectSelectedCluster, useTopicBrowserStore } from '../../store/useTopicBrowserStore'
import type { Topic } from '../../types'

export function ActiveFiltersBar() {
  const searchQuery = useTopicBrowserStore((s) => s.searchQuery)
  const interestBucketSlugs = useTopicBrowserStore((s) => s.interestBucketSlugs)
  const pathFilterVideoIds = useTopicBrowserStore((s) => s.pathFilterVideoIds)
  const pathFilterTitle = useTopicBrowserStore((s) => s.pathFilterTitle)
  const selectedTopicIds = useTopicBrowserStore((s) => s.selectedTopicIds)
  const allTopics = useTopicBrowserStore((s) => s.allTopics)
  const clearCluster = useTopicBrowserStore((s) => s.clearCluster)
  const clearSearch = useTopicBrowserStore((s) => s.clearSearch)
  const clearPathFilter = useTopicBrowserStore((s) => s.clearPathFilter)
  const clearAllFilters = useTopicBrowserStore((s) => s.clearAllFilters)
  const setSelectedTopicIds = useTopicBrowserStore((s) => s.setSelectedTopicIds)

  const filteredVideos = useFilteredVideos()
  const filteredCount = filteredVideos.length

  const topics = useMemo(
    () =>
      selectedTopicIds
        .map((id) => allTopics.find((t) => t.id === id))
        .filter((t): t is Topic => t != null),
    [selectedTopicIds, allTopics],
  )
  const cluster = useTopicBrowserStore(selectSelectedCluster)

  const hasPathFilter =
    pathFilterVideoIds != null && pathFilterVideoIds.length > 0

  const hasInterestFilter =
    interestBucketSlugs != null && interestBucketSlugs.length > 0

  const hasFilters =
    topics.length > 0 ||
    hasInterestFilter ||
    cluster != null ||
    searchQuery.trim().length > 0 ||
    hasPathFilter

  const parts: string[] = []
  if (hasPathFilter) {
    parts.push(`Path: ${pathFilterTitle ?? 'Learning path'}`)
  }
  if (hasInterestFilter) {
    parts.push(`Interest (${interestBucketSlugs!.slice(0, 3).join(', ')}${interestBucketSlugs!.length > 3 ? '…' : ''})`)
  }
  for (const t of topics) parts.push(t.name)
  if (cluster) parts.push(cluster.name)
  if (searchQuery.trim()) parts.push(`"${searchQuery.trim()}"`)

  const summary =
    parts.length > 0 ? parts.join(' + ') : 'all videos'

  function removeTopic(id: string) {
    setSelectedTopicIds(selectedTopicIds.filter((x) => x !== id))
  }

  return (
    <div className="rounded-lg border border-zinc-700/80 bg-zinc-900/50 px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-zinc-500">
          Filtered by:
        </span>
        {hasInterestFilter ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-950/40 px-2.5 py-1 text-xs text-amber-200 ring-1 ring-amber-800/50">
            Interest
            <button
              type="button"
              className="shrink-0 rounded p-0.5 hover:bg-amber-900/80"
              onClick={() => useTopicBrowserStore.getState().setInterestBucketSlugs(null)}
              aria-label="Clear interest filter"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        ) : null}
        {hasPathFilter ? (
          <span className="inline-flex max-w-[min(100%,280px)] items-center gap-1 rounded-full bg-violet-950/50 px-2.5 py-1 text-xs text-violet-200 ring-1 ring-violet-700/40">
            <span className="truncate" title={pathFilterTitle ?? undefined}>
              Path: {pathFilterTitle ?? 'Untitled'}
            </span>
            <button
              type="button"
              className="shrink-0 rounded p-0.5 hover:bg-violet-900/80"
              onClick={clearPathFilter}
              aria-label="Clear path filter"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        ) : null}
        {topics.map((t) => (
          <span
            key={t.id}
            className="inline-flex items-center gap-1 rounded-full bg-zinc-800 px-2.5 py-1 text-xs text-zinc-200"
          >
            {t.name}
            <button
              type="button"
              className="rounded p-0.5 hover:bg-zinc-700"
              onClick={() => removeTopic(t.id)}
              aria-label={`Remove topic ${t.name}`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        ))}
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

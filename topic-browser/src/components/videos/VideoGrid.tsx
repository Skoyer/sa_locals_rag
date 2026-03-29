import { useEffect, useRef } from 'react'

import { useFilteredVideos } from '../../hooks/useFilteredVideos'
import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'
import { VideoCard } from './VideoCard'

interface VideoGridProps {
  loading: boolean
}

function filterKey(
  topicIds: string[],
  interestSlugs: string[] | null,
  clusterId: number | null,
  q: string,
  pathIds: number[] | null,
): string {
  const pathPart =
    pathIds && pathIds.length > 0 ? pathIds.join(',') : ''
  const interestPart =
    interestSlugs && interestSlugs.length > 0
      ? interestSlugs.join(',')
      : ''
  return `${topicIds.join(',')}|${interestPart}|${clusterId ?? ''}|${q}|${pathPart}`
}

export function VideoGrid({ loading }: VideoGridProps) {
  const filteredVideos = useFilteredVideos()
  const selectedTopicIds = useTopicBrowserStore((s) => s.selectedTopicIds)
  const selectedClusterId = useTopicBrowserStore((s) => s.selectedClusterId)
  const searchQuery = useTopicBrowserStore((s) => s.searchQuery)
  const pathFilterVideoIds = useTopicBrowserStore(
    (s) => s.pathFilterVideoIds,
  )
  const pathPreviewMode = useTopicBrowserStore((s) => s.pathPreviewMode)
  const interestBucketSlugs = useTopicBrowserStore(
    (s) => s.interestBucketSlugs,
  )

  const sectionRef = useRef<HTMLElement>(null)
  const skipScrollRef = useRef(true)

  useEffect(() => {
    if (skipScrollRef.current) {
      skipScrollRef.current = false
      return
    }
    const t = window.setTimeout(() => {
      if (
        window.matchMedia('(max-width: 768px)').matches &&
        sectionRef.current
      ) {
        sectionRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }
    }, 40)
    return () => clearTimeout(t)
  }, [
    selectedTopicIds,
    interestBucketSlugs,
    selectedClusterId,
    searchQuery,
    pathFilterVideoIds,
  ])

  if (loading) {
    return (
      <section
        className="rounded-lg border border-zinc-800 p-4"
        aria-busy="true"
        aria-label="Loading videos"
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="tb-shimmer h-40 rounded-lg border border-zinc-800"
            />
          ))}
        </div>
      </section>
    )
  }

  if (filteredVideos.length === 0) {
    const emptyDraft =
      pathPreviewMode &&
      pathFilterVideoIds != null &&
      pathFilterVideoIds.length === 0
    return (
      <section
        ref={sectionRef}
        className="rounded-lg border border-dashed border-zinc-600 bg-zinc-900/40 px-6 py-12 text-center"
      >
        {emptyDraft ? (
          <>
            <p className="text-zinc-300">
              This path is empty. Add videos from Topics/Clusters or clear and
              start again.
            </p>
            <p className="mt-2 text-sm text-zinc-500">
              Use the sidebar or search to find lessons, then use &apos;Add to
              path&apos; on each card.
            </p>
          </>
        ) : (
          <>
            <p className="text-zinc-300">
              No videos match your search and filters.
            </p>
            <p className="mt-2 text-sm text-zinc-500">
              Try clearing filters or broadening your search.
            </p>
          </>
        )}
      </section>
    )
  }

  const gridKey = filterKey(
    selectedTopicIds,
    interestBucketSlugs,
    selectedClusterId,
    searchQuery,
    pathFilterVideoIds,
  )

  return (
    <section ref={sectionRef} className="space-y-3">
      {pathPreviewMode ? (
        <p className="text-xs text-amber-200/90" aria-live="polite">
          You have {pathFilterVideoIds?.length ?? 0} video
          {(pathFilterVideoIds?.length ?? 0) === 1 ? '' : 's'} in your custom
          path draft. Use &apos;Remove from path&apos; or &apos;Add to
          path&apos; on any video card to customize.
        </p>
      ) : (
        <p className="text-xs text-zinc-500" aria-live="polite">
          Results update as you refine topics, clusters, or search.
        </p>
      )}
      <div
        key={gridKey}
        className="tb-fade-in grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        {filteredVideos.map((v) => (
          <VideoCard key={v.id} video={v} />
        ))}
      </div>
    </section>
  )
}

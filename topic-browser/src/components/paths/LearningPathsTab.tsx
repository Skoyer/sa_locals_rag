import { BookOpen, ExternalLink, ListVideo } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import {
  INTEREST_TILES,
  localInterestPathId,
  topicIdsForInterestBuckets,
  videoMatchesInterestBuckets,
  type InterestId,
} from '../../data/interestBuckets'
import { getInterestStarterVideoIds } from '../../data/interestStarterPath'
import {
  LOCAL_WATCH_EVERYTHING_PATH_ID,
  orderWatchEverythingVideos,
  remainingUnwatchedVideos,
  WATCH_EVERYTHING_TITLE,
} from '../../data/watchEverythingOrder'
import { useFilteredVideos } from '../../hooks/useFilteredVideos'
import { isSupabaseConfigured, supabase } from '../../lib/supabaseClient'
import { useAuthStore } from '../../store/useAuthStore'
import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'
import type { FeaturedLearningPath, VideoProgress } from '../../types'
import { featuredPathForInterest } from './featuredMatch'
import { CreatePathModal } from './CreatePathModal'
import { InterestGrid } from './InterestGrid'
import { InterestModal } from './InterestModal'

interface FeaturedPathRow {
  id: string
  title: string
  description: string | null
  tags: string[] | null
  video_ids: number[]
  created_at: string
}

function mapFeaturedRow(row: FeaturedPathRow): FeaturedLearningPath {
  return {
    kind: 'featured',
    id: row.id,
    title: row.title,
    description: row.description,
    tags: row.tags ?? [],
    videoIds: row.video_ids ?? [],
    createdAt: row.created_at,
  }
}

function completedCount(
  videoIds: number[],
  progress: VideoProgress[] | undefined,
): number {
  const rows = progress ?? []
  const watched = new Set(rows.map((p) => p.videoId))
  return videoIds.filter((id) => watched.has(id)).length
}

interface LearningPathsTabProps {
  onViewPathInGrid: (
    videoIds: number[],
    title: string,
    pathId?: string | null,
    options?: { preview?: boolean; defaultSaveTitle?: string | null },
  ) => void
  onTabChange: (tab: 'videos' | 'paths') => void
}

export function LearningPathsTab({
  onViewPathInGrid,
  onTabChange,
}: LearningPathsTabProps) {
  const user = useAuthStore((s) => s.user)
  const guestId = useAuthStore((s) => s.guestId)
  const userPaths = useAuthStore((s) => s.userPaths)
  const guestPaths = useAuthStore((s) => s.guestPaths)
  const progress = useAuthStore((s) =>
    s.user ? s.progress : s.guestProgress,
  )
  const saveUserPathFromVideoIds = useAuthStore(
    (s) => s.saveUserPathFromVideoIds,
  )

  const allVideos = useTopicBrowserStore((s) => s.allVideos)
  const allTopics = useTopicBrowserStore((s) => s.allTopics)
  const setSelectedTopicIds = useTopicBrowserStore((s) => s.setSelectedTopicIds)
  const clearAllFilters = useTopicBrowserStore((s) => s.clearAllFilters)
  const clearTopic = useTopicBrowserStore((s) => s.clearTopic)

  const filteredVideos = useFilteredVideos()
  const videoIdsForPath = filteredVideos.map((v) => v.id)

  const [featured, setFeatured] = useState<FeaturedLearningPath[]>([])
  const [loadingFeatured, setLoadingFeatured] = useState(isSupabaseConfigured)
  const [createOpen, setCreateOpen] = useState(false)
  const [interestModalId, setInterestModalId] = useState<InterestId | null>(
    null,
  )
  const [pathsBanner, setPathsBanner] = useState<string | null>(null)

  const interestTile = useMemo(
    () =>
      interestModalId
        ? INTEREST_TILES.find((t) => t.id === interestModalId) ?? null
        : null,
    [interestModalId],
  )

  const interestVideoCount = useMemo(() => {
    if (!interestTile) return 0
    return allVideos.filter((v) =>
      videoMatchesInterestBuckets(v.topic_buckets, interestTile.bucketSlugs),
    ).length
  }, [allVideos, interestTile])

  const interestFeaturedPath = useMemo(() => {
    if (!interestModalId) return null
    return featuredPathForInterest(interestModalId, featured)
  }, [interestModalId, featured])

  const primaryVideoIds = useMemo(() => {
    if (!interestModalId) return []
    const fp = interestFeaturedPath
    if (fp && fp.videoIds.length > 0) return fp.videoIds
    const tile = INTEREST_TILES.find((t) => t.id === interestModalId)
    if (!tile) return []
    return getInterestStarterVideoIds(allVideos, tile.bucketSlugs)
  }, [interestModalId, interestFeaturedPath, allVideos])

  const hasFeaturedPath = !!(
    interestFeaturedPath && interestFeaturedPath.videoIds.length > 0
  )

  const watchedIds = useMemo(
    () => new Set((progress ?? []).map((p) => p.videoId)),
    [progress],
  )

  const remainingVideos = useMemo(
    () => remainingUnwatchedVideos(allVideos, watchedIds),
    [allVideos, watchedIds],
  )

  const watchEverythingOrderedIds = useMemo(
    () => orderWatchEverythingVideos(remainingVideos),
    [remainingVideos],
  )

  useEffect(() => {
    if (!isSupabaseConfigured) return
    let cancelled = false
    void supabase
      .from('featured_learning_paths')
      .select('*')
      .order('created_at', { ascending: true })
      .then(({ data, error }) => {
        if (cancelled) return
        if (error) {
          console.warn('featured_learning_paths:', error.message)
          setFeatured([])
        } else {
          setFeatured(
            (data as FeaturedPathRow[] | null)?.map(mapFeaturedRow) ?? [],
          )
        }
        setLoadingFeatured(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSavePath(title: string, description: string) {
    const result = await saveUserPathFromVideoIds(
      title,
      description || undefined,
      videoIdsForPath,
    )
    if (!result.ok) {
      throw new Error(result.error ?? 'Could not save path.')
    }
  }

  function handleSelectInterest(id: InterestId) {
    const tile = INTEREST_TILES.find((t) => t.id === id)
    if (!tile) return
    const existing = new Set(allTopics.map((t) => t.id))
    setSelectedTopicIds(topicIdsForInterestBuckets(tile.bucketSlugs, existing))
    setInterestModalId(id)
  }

  async function handleInterestPrimary() {
    if (!interestModalId || !interestTile) return
    const title = `${interestTile.label} — ${primaryVideoIds.length}-lesson starter path`

    if (hasFeaturedPath && interestFeaturedPath) {
      onViewPathInGrid(
        interestFeaturedPath.videoIds,
        title,
        interestFeaturedPath.id,
      )
    } else if (primaryVideoIds.length === 0) {
      return
    } else if (user && isSupabaseConfigured) {
      const r = await saveUserPathFromVideoIds(
        `${interestTile.label} Starter`,
        `Default starter for ${interestTile.label}.`,
        primaryVideoIds,
      )
      if (r.ok) {
        onViewPathInGrid(primaryVideoIds, title, r.pathId ?? null)
      } else {
        onViewPathInGrid(
          primaryVideoIds,
          title,
          localInterestPathId(interestModalId),
        )
      }
    } else if (guestId && primaryVideoIds.length > 0) {
      const r = await saveUserPathFromVideoIds(
        `${interestTile.label} Starter`,
        `Default starter for ${interestTile.label}.`,
        primaryVideoIds,
      )
      if (r.ok) {
        onViewPathInGrid(primaryVideoIds, title, r.pathId ?? null)
      } else {
        onViewPathInGrid(
          primaryVideoIds,
          title,
          localInterestPathId(interestModalId),
        )
      }
    } else {
      onViewPathInGrid(
        primaryVideoIds,
        title,
        localInterestPathId(interestModalId),
      )
    }
    clearTopic()
    setInterestModalId(null)
  }

  function handleInterestReview() {
    if (!interestModalId || !interestTile) return
    const title = `${interestTile.label} — ${primaryVideoIds.length}-lesson starter path`
    onViewPathInGrid(primaryVideoIds, title, null, {
      preview: true,
      defaultSaveTitle: `${interestTile.label} — My custom path`,
    })
    clearTopic()
    setInterestModalId(null)
  }

  function handleWatchEverythingStart() {
    if (watchEverythingOrderedIds.length === 0) {
      setPathsBanner("You've already watched every lesson. Great work!")
      return
    }
    onViewPathInGrid(
      watchEverythingOrderedIds,
      WATCH_EVERYTHING_TITLE,
      LOCAL_WATCH_EVERYTHING_PATH_ID,
    )
  }

  return (
    <div className="space-y-10">
      {pathsBanner ? (
        <p className="rounded-lg border border-emerald-800/50 bg-emerald-950/30 px-4 py-3 text-sm text-emerald-200">
          {pathsBanner}
          <button
            type="button"
            className="ml-2 text-emerald-400 underline"
            onClick={() => setPathsBanner(null)}
          >
            Dismiss
          </button>
        </p>
      ) : null}

      <InterestGrid onSelectInterest={handleSelectInterest} />

      <div className="relative text-center">
        <div className="absolute inset-x-0 top-1/2 border-t border-zinc-800" />
        <span className="relative bg-zinc-950 px-3 text-xs text-zinc-500">
          or browse all videos
        </span>
      </div>
      <div className="flex justify-center">
        <button
          type="button"
          className="rounded-lg border border-zinc-600 px-4 py-2 text-sm font-medium text-zinc-200 hover:bg-zinc-800"
          onClick={() => {
            clearAllFilters()
            onTabChange('videos')
          }}
        >
          Browse all videos
        </button>
      </div>

      <section>
        <h2 className="flex items-center gap-2 text-lg font-semibold text-zinc-100">
          <BookOpen className="h-5 w-5 text-violet-400" aria-hidden />
          Featured paths
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          Curated paths visible to everyone (managed in Supabase).
        </p>
        {loadingFeatured ? (
          <p className="mt-4 text-sm text-zinc-500">Loading…</p>
        ) : featured.length === 0 ? (
          <p className="mt-4 rounded-lg border border-dashed border-zinc-700 bg-zinc-900/40 px-4 py-6 text-sm text-zinc-500">
            No featured paths yet. Add rows to{' '}
            <code className="rounded bg-zinc-800 px-1">
              featured_learning_paths
            </code>{' '}
            in the Supabase SQL editor.
          </p>
        ) : (
          <ul className="mt-4 grid gap-4 sm:grid-cols-2">
            {featured.map((path) => (
              <PathCard
                key={path.id}
                title={path.title}
                description={path.description}
                tags={path.tags}
                videoIds={path.videoIds}
                completed={completedCount(path.videoIds, progress)}
                onViewInGrid={() =>
                  onViewPathInGrid(path.videoIds, path.title, path.id)
                }
              />
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="flex items-center gap-2 text-lg font-semibold text-zinc-100">
          <ListVideo className="h-5 w-5 text-violet-400" aria-hidden />
          Your paths
        </h2>
        {!user ? (
          <p className="mt-4 rounded-lg border border-zinc-700 bg-zinc-900/50 px-4 py-6 text-sm text-zinc-400">
            Your paths are stored in this browser only. Sign in to access them
            from any device.
          </p>
        ) : null}

        <ul className="mt-4 grid gap-4 sm:grid-cols-2">
          {allVideos.length > 0 ? (
            <WatchEverythingCard
              allWatched={
                allVideos.length > 0 && remainingVideos.length === 0
              }
              hasUnwatched={remainingVideos.length > 0}
              canTrackProgress={!!user || !!guestId}
              onStart={handleWatchEverythingStart}
            />
          ) : null}
          {(user || guestId) &&
          (user ? userPaths : guestPaths).length === 0 ? (
            <li className="flex flex-col rounded-xl border border-dashed border-zinc-700 bg-zinc-900/40 p-4">
              <p className="text-sm text-zinc-400">
                You don&apos;t have any saved paths yet. Use the Videos tab to
                filter the list, then create a path from the current results.
              </p>
              <button
                type="button"
                className="mt-4 self-start rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
                disabled={videoIdsForPath.length === 0}
                onClick={() => setCreateOpen(true)}
              >
                Create path from current filters
              </button>
            </li>
          ) : null}
          {user
            ? userPaths.map((path) => (
                <PathCard
                  key={path.id}
                  title={path.title}
                  description={path.description}
                  tags={path.tags}
                  videoIds={path.videoIds}
                  completed={completedCount(path.videoIds, progress)}
                  onViewInGrid={() =>
                    onViewPathInGrid(path.videoIds, path.title, path.id)
                  }
                />
              ))
            : guestPaths.map((path) => (
                <PathCard
                  key={path.id}
                  title={path.title}
                  description={path.description}
                  tags={path.tags}
                  videoIds={path.videoIds}
                  completed={completedCount(path.videoIds, progress)}
                  onViewInGrid={() =>
                    onViewPathInGrid(path.videoIds, path.title, path.id)
                  }
                />
              ))}
        </ul>

        {(user || guestId) &&
        (user ? userPaths : guestPaths).length > 0 ? (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="rounded-lg border border-violet-500/50 bg-violet-950/40 px-4 py-2 text-sm font-medium text-violet-200 hover:bg-violet-950/70 disabled:opacity-50"
              disabled={videoIdsForPath.length === 0}
              onClick={() => setCreateOpen(true)}
            >
              Create path from current filters
            </button>
          </div>
        ) : null}
      </section>

      <CreatePathModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSave={handleSavePath}
        videoCount={videoIdsForPath.length}
      />

      {interestModalId && interestTile ? (
        <InterestModal
          open
          interestLabel={interestTile.label}
          interestIcon={interestTile.icon}
          primaryVideoIds={primaryVideoIds}
          matchCount={interestVideoCount}
          hasFeaturedPath={hasFeaturedPath}
          canSaveUserPath={!!user || !!guestId}
          guestMode={!!guestId && !user}
          onClose={() => {
            clearTopic()
            setInterestModalId(null)
          }}
          onPrimary={() => void handleInterestPrimary()}
          onReviewCustomize={handleInterestReview}
        />
      ) : null}
    </div>
  )
}

function WatchEverythingCard({
  allWatched,
  hasUnwatched,
  canTrackProgress,
  onStart,
}: {
  allWatched: boolean
  hasUnwatched: boolean
  canTrackProgress: boolean
  onStart: () => void
}) {
  function focusAuthEmail() {
    document.getElementById('auth-email')?.focus()
  }

  if (allWatched && canTrackProgress) {
    return (
      <li className="flex flex-col rounded-xl border border-zinc-700/80 bg-zinc-900/60 p-4">
        <h3 className="font-medium text-zinc-100">You&apos;ve watched every lesson!</h3>
        <p className="mt-2 text-sm text-zinc-500">
          New lessons will appear here when available.
        </p>
      </li>
    )
  }

  if (!canTrackProgress) {
    return (
      <li className="flex flex-col rounded-xl border border-zinc-700/80 bg-zinc-900/60 p-4">
        <h3 className="font-medium text-zinc-100">
          Everything you haven&apos;t watched yet
        </h3>
        <p className="mt-2 text-sm text-zinc-500">
          Continue through all remaining lessons in a smart order.
        </p>
        <p className="mt-3 text-sm text-zinc-500">
          Sign in to track what you&apos;ve watched and finish the whole library.
        </p>
        <button
          type="button"
          className="mt-4 self-start rounded-lg border border-violet-500/50 bg-violet-950/40 px-4 py-2 text-sm font-medium text-violet-200 hover:bg-violet-950/70"
          onClick={focusAuthEmail}
        >
          Sign in
        </button>
      </li>
    )
  }

  return (
    <li className="flex flex-col rounded-xl border border-violet-800/40 bg-violet-950/20 p-4">
      <h3 className="font-medium text-zinc-100">
        Everything you haven&apos;t watched yet
      </h3>
      <p className="mt-2 text-sm text-zinc-500">
        Continue through all remaining lessons in a smart order.
      </p>
      {hasUnwatched ? (
        <button
          type="button"
          className="mt-4 self-start rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
          onClick={onStart}
        >
          Start &apos;Watch Everything&apos; path
        </button>
      ) : null}
    </li>
  )
}

function PathCard({
  title,
  description,
  tags,
  videoIds,
  completed,
  onViewInGrid,
}: {
  title: string
  description?: string | null
  tags: string[]
  videoIds: number[]
  completed: number
  onViewInGrid: () => void
}) {
  const total = videoIds.length
  return (
    <li className="flex flex-col rounded-xl border border-zinc-700/80 bg-zinc-900/60 p-4">
      <h3 className="font-medium text-zinc-100">{title}</h3>
      {description ? (
        <p className="mt-2 line-clamp-3 text-sm text-zinc-400">{description}</p>
      ) : null}
      {tags.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {tags.map((t) => (
            <span
              key={t}
              className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400"
            >
              {t}
            </span>
          ))}
        </div>
      ) : null}
      <p className="mt-3 text-sm text-zinc-500">
        <strong className="text-zinc-300">{completed}</strong> of{' '}
        <strong className="text-zinc-300">{total}</strong> videos completed
      </p>
      <button
        type="button"
        className="mt-4 inline-flex items-center gap-1.5 self-start rounded-lg border border-zinc-600 px-3 py-1.5 text-sm text-violet-300 hover:bg-zinc-800"
        onClick={onViewInGrid}
      >
        View in grid
        <ExternalLink className="h-3.5 w-3.5" aria-hidden />
      </button>
    </li>
  )
}

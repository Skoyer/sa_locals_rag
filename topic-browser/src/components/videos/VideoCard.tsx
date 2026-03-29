import { MinusCircle, PlusCircle } from 'lucide-react'

import { useAuthStore } from '../../store/useAuthStore'
import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'
import type { Video } from '../../types'

function difficultyClass(d: string): string {
  if (d === 'beginner') return 'bg-emerald-900/70 text-emerald-200'
  if (d === 'advanced') return 'bg-red-900/70 text-red-200'
  return 'bg-amber-900/70 text-amber-200'
}

interface VideoCardProps {
  video: Video
}

export function VideoCard({ video }: VideoCardProps) {
  const user = useAuthStore((s) => s.user)
  const guestId = useAuthStore((s) => s.guestId)
  const progress = useAuthStore((s) =>
    s.user ? s.progress : s.guestProgress,
  )
  const toggleVideoWatched = useAuthStore((s) => s.toggleVideoWatched)

  const pathPreviewMode = useTopicBrowserStore((s) => s.pathPreviewMode)
  const pathFilterVideoIds = useTopicBrowserStore((s) => s.pathFilterVideoIds)
  const removeVideoFromPathDraft = useTopicBrowserStore(
    (s) => s.removeVideoFromPathDraft,
  )
  const addVideoToPathDraft = useTopicBrowserStore((s) => s.addVideoToPathDraft)

  const isWatched = progress.some((p) => p.videoId === video.id)
  const inDraft =
    pathPreviewMode &&
    pathFilterVideoIds != null &&
    pathFilterVideoIds.includes(video.id)

  const wc = video.wordcloud_path?.trim()
  const imgSrc = wc ? `/${wc.replace(/^\//, '')}` : ''

  const short = video.short_title?.trim()
  const heading = short || video.title || '(no title)'
  const originalTitle = video.title?.trim() ?? ''

  const showReviewControls = pathPreviewMode && pathFilterVideoIds != null

  return (
    <article className="flex flex-col rounded-lg border border-zinc-700/80 bg-zinc-900/60 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="min-w-0 flex-1 text-base font-medium leading-snug text-zinc-100">
          {video.url ? (
            <a
              href={video.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-violet-300 hover:text-violet-200 hover:underline"
            >
              {heading}
            </a>
          ) : (
            <span>{heading}</span>
          )}{' '}
          <span
            className={`ml-1 inline-block rounded px-1.5 py-0.5 align-middle text-xs ${difficultyClass(video.difficulty || 'intermediate')}`}
          >
            {video.difficulty || 'intermediate'}
          </span>
        </h3>
        {isWatched ? (
          <span className="shrink-0 rounded bg-emerald-950/80 px-2 py-0.5 text-xs font-medium text-emerald-300 ring-1 ring-emerald-700/50">
            ✓ Watched
          </span>
        ) : null}
      </div>
      {short && originalTitle ? (
        <p className="mt-1 line-clamp-2 text-xs text-zinc-600">{originalTitle}</p>
      ) : null}
      <p className="mt-2 line-clamp-4 text-sm text-zinc-400">
        {video.core_lesson || video.summary_text || ''}
      </p>
      {(video.topics ?? []).length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1">
          {(video.topics ?? []).map((t) => (
            <span
              key={t.id}
              className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300"
            >
              {t.name}
            </span>
          ))}
        </div>
      ) : null}
      {video.cluster ? (
        <p className="mt-2 text-xs text-zinc-500">
          Cluster: {video.cluster.name}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-zinc-800 pt-3">
        {user ? (
          <button
            type="button"
            className="text-sm text-violet-400 hover:text-violet-300 hover:underline"
            onClick={() => void toggleVideoWatched(video.id)}
          >
            {isWatched ? 'Mark unwatched' : 'Mark as watched'}
          </button>
        ) : guestId ? (
          <button
            type="button"
            className="text-sm text-violet-400 hover:text-violet-300 hover:underline"
            onClick={() => void toggleVideoWatched(video.id)}
          >
            {isWatched ? 'Mark unwatched' : 'Mark as watched'}
          </button>
        ) : null}
        {showReviewControls ? (
          inDraft ? (
            <button
              type="button"
              className="inline-flex items-center gap-1 text-sm text-rose-300 hover:text-rose-200"
              onClick={() => removeVideoFromPathDraft(video.id)}
            >
              <MinusCircle className="h-4 w-4 shrink-0" aria-hidden />
              Remove from path
            </button>
          ) : (
            <button
              type="button"
              className="inline-flex items-center gap-1 text-sm text-emerald-400 hover:text-emerald-300"
              onClick={() => addVideoToPathDraft(video.id)}
            >
              <PlusCircle className="h-4 w-4 shrink-0" aria-hidden />
              Add to path
            </button>
          )
        ) : null}
        {showReviewControls && !user && guestId ? (
          <p className="text-xs text-zinc-500">
            In guest mode — sign in later to keep this path.
          </p>
        ) : null}
        {!user && !guestId && !showReviewControls ? (
          <p className="text-xs text-zinc-600">Sign in to track progress</p>
        ) : null}
      </div>
      {imgSrc ? (
        <img
          src={imgSrc}
          alt=""
          className="mt-3 h-24 w-full rounded object-cover"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.style.display = 'none'
          }}
        />
      ) : null}
    </article>
  )
}

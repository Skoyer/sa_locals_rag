import { useState } from 'react'

import { useAuthStore } from '../../store/useAuthStore'
import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'
import { CreatePathModal } from '../paths/CreatePathModal'

interface PathProgressBarProps {
  onBackToPaths: () => void
  onTabChange: (tab: 'videos' | 'paths') => void
  onPathSaved?: () => void
}

export function PathProgressBar({
  onBackToPaths,
  onTabChange,
  onPathSaved,
}: PathProgressBarProps) {
  const pathFilterTitle = useTopicBrowserStore((s) => s.pathFilterTitle)
  const pathFilterVideoIds = useTopicBrowserStore((s) => s.pathFilterVideoIds)
  const pathPreviewMode = useTopicBrowserStore((s) => s.pathPreviewMode)
  const reviewDraftDefaultTitle = useTopicBrowserStore(
    (s) => s.reviewDraftDefaultTitle,
  )
  const clearPathFilter = useTopicBrowserStore((s) => s.clearPathFilter)

  const user = useAuthStore((s) => s.user)
  const guestId = useAuthStore((s) => s.guestId)
  const progress = useAuthStore((s) =>
    s.user ? s.progress : s.guestProgress,
  )
  const saveUserPathFromVideoIds = useAuthStore(
    (s) => s.saveUserPathFromVideoIds,
  )

  const [saveOpen, setSaveOpen] = useState(false)

  const canSave =
    pathPreviewMode &&
    pathFilterVideoIds != null &&
    pathFilterVideoIds.length > 0 &&
    (user != null || guestId != null)

  const showBar =
    pathFilterVideoIds != null &&
    (pathPreviewMode || pathFilterVideoIds.length > 0)

  if (!showBar) {
    return null
  }

  const ids = pathFilterVideoIds ?? []
  const total = ids.length
  const watchedSet = new Set(progress.map((p) => p.videoId))
  const done = ids.filter((id) => watchedSet.has(id)).length
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  async function handleSave(title: string, description: string) {
    if (!pathFilterVideoIds || pathFilterVideoIds.length === 0) return
    const result = await saveUserPathFromVideoIds(
      title,
      description || undefined,
      pathFilterVideoIds,
    )
    if (!result.ok) throw new Error(result.error ?? 'Could not save path.')
    clearPathFilter()
    setSaveOpen(false)
    onPathSaved?.()
    onTabChange('paths')
  }

  return (
    <>
      <div className="rounded-lg border border-violet-800/50 bg-violet-950/30 px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium text-violet-100">
                Path: {pathFilterTitle ?? 'Learning path'}
              </p>
              {pathPreviewMode ? (
                <button
                  type="button"
                  className="shrink-0 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={!canSave}
                  title={
                    total === 0
                      ? 'Add at least one video to your draft.'
                      : !user && guestId
                        ? 'Saved to this browser only until you sign in.'
                        : !user && !guestId
                          ? 'Sign in to save your custom path.'
                          : undefined
                  }
                  onClick={() => setSaveOpen(true)}
                >
                  Save as my custom path
                </button>
              ) : null}
            </div>
            <div className="mt-2 flex items-center gap-3">
              <div
                className="h-2 min-w-[120px] flex-1 max-w-md overflow-hidden rounded-full bg-zinc-800"
                role="progressbar"
                aria-valuenow={done}
                aria-valuemin={0}
                aria-valuemax={Math.max(total, 1)}
              >
                <div
                  className="h-full rounded-full bg-violet-500 transition-[width]"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="shrink-0 text-sm tabular-nums text-zinc-300">
                {done} of {total}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="shrink-0 text-sm text-violet-300 hover:text-violet-200 hover:underline"
            onClick={onBackToPaths}
          >
            ← Back to paths
          </button>
        </div>
      </div>
      <CreatePathModal
        open={saveOpen}
        onClose={() => setSaveOpen(false)}
        onSave={handleSave}
        videoCount={ids.length}
        initialTitle={reviewDraftDefaultTitle ?? ''}
      />
    </>
  )
}

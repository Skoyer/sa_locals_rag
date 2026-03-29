import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'

export function PathPreviewBanner() {
  const pathPreviewMode = useTopicBrowserStore((s) => s.pathPreviewMode)
  const pathFilterVideoIds = useTopicBrowserStore((s) => s.pathFilterVideoIds)
  const clearPathFilter = useTopicBrowserStore((s) => s.clearPathFilter)

  if (!pathPreviewMode || pathFilterVideoIds === null) {
    return null
  }

  const count = pathFilterVideoIds.length

  return (
    <div className="rounded-lg border border-amber-800/50 bg-amber-950/25 px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-2">
          <p className="text-sm text-amber-100">
            You&apos;re reviewing this starter set. Remove any lessons you
            don&apos;t want, add new ones from the sidebar or search, then save
            it as your own path.
          </p>
          <p className="text-xs text-amber-200/90">
            You have {count} video{count === 1 ? '' : 's'} in your custom path
            draft. Use &apos;Remove from path&apos; or &apos;Add to path&apos; on
            any video card to customize.
          </p>
        </div>
        <button
          type="button"
          className="shrink-0 text-sm text-amber-300 underline hover:text-amber-200"
          onClick={() => clearPathFilter()}
        >
          Clear review
        </button>
      </div>
    </div>
  )
}

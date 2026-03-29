import { X } from 'lucide-react'

import { isSupabaseConfigured } from '../../lib/supabaseClient'

interface InterestModalProps {
  open: boolean
  interestLabel: string
  interestIcon: string
  /** Ordered ids for the starter path (featured or computed). */
  primaryVideoIds: number[]
  /** Total lessons matching the interest buckets (may exceed path length). */
  matchCount: number
  /** True when a Supabase featured path with videos is selected for this interest. */
  hasFeaturedPath: boolean
  canSaveUserPath: boolean
  /** Guest can persist paths locally without Supabase. */
  guestMode?: boolean
  onClose: () => void
  onPrimary: () => void
  onReviewCustomize: () => void
}

export function InterestModal({
  open,
  interestLabel,
  interestIcon,
  primaryVideoIds,
  matchCount,
  hasFeaturedPath,
  canSaveUserPath,
  guestMode = false,
  onClose,
  onPrimary,
  onReviewCustomize,
}: InterestModalProps) {
  if (!open) return null

  const n = primaryVideoIds.length
  const titleLine = `${interestLabel} — ${n}-lesson starter path`
  const showCreateStarter =
    !hasFeaturedPath &&
    n > 0 &&
    canSaveUserPath &&
    (guestMode || isSupabaseConfigured)
  const primaryLabel = showCreateStarter
    ? `Create a starter path from these ${n} videos`
    : `Start this ${interestLabel} path`

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="interest-modal-title"
        className="relative w-full max-w-lg rounded-xl border border-zinc-600 bg-zinc-900 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="absolute right-3 top-3 rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
          onClick={onClose}
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>
        <p id="interest-modal-title" className="pr-8 text-lg font-semibold text-zinc-100">
          <span aria-hidden>{interestIcon}</span> {interestLabel} — {matchCount} lesson
          {matchCount === 1 ? '' : 's'} found
        </p>
        <p className="mt-2 text-sm text-zinc-500">
          Start with the recommended path or review the full matching list.
        </p>

        {n > 0 ? (
          <div className="mt-6 rounded-lg border border-zinc-700 bg-zinc-950/50 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Recommended
            </p>
            <h3 className="mt-1 font-medium text-zinc-100">{titleLine}</h3>
            <p className="mt-2 text-sm text-zinc-400">
              We&apos;ve picked a sequence of lessons to build your {interestLabel.toLowerCase()}{' '}
              skills step by step.
            </p>
            <button
              type="button"
              className="mt-4 w-full rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
              onClick={onPrimary}
              disabled={n === 0}
            >
              {primaryLabel}
            </button>
            <button
              type="button"
              className="mt-3 w-full rounded-lg border border-zinc-600 px-4 py-2.5 text-sm font-medium text-zinc-200 hover:bg-zinc-800"
              onClick={onReviewCustomize}
              disabled={n === 0}
            >
              Review and customize these {n} videos
            </button>
          </div>
        ) : (
          <p className="mt-6 rounded-lg border border-dashed border-zinc-700 px-4 py-3 text-sm text-zinc-500">
            No lessons match this interest yet.
          </p>
        )}
      </div>
    </div>
  )
}

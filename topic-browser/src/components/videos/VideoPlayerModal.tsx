import { X } from 'lucide-react'
import { useEffect, useRef } from 'react'

import type { Video } from '../../types'

interface VideoPlayerModalProps {
  video: Video
  onClose: () => void
}

/** In-app player for locally downloaded files served by ``local_media``. */
export function VideoPlayerModal({ video, onClose }: VideoPlayerModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const src = `/media/video/${video.id}`

  useEffect(() => {
    const el = dialogRef.current
    if (!el) return
    if (!el.open) el.showModal()
    const onCancel = (e: Event) => {
      e.preventDefault()
      onClose()
    }
    el.addEventListener('cancel', onCancel)
    return () => el.removeEventListener('cancel', onCancel)
  }, [onClose])

  const heading =
    video.short_title?.trim() || video.title?.trim() || 'Local video'

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 m-0 flex h-full max-h-none w-full max-w-none items-center justify-center bg-black/80 p-4 text-zinc-100 open:flex"
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose()
      }}
    >
      <div
        className="relative flex w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-zinc-700 bg-zinc-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-zinc-800 px-4 py-3">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-400/90">
              Local file
            </p>
            <h2 className="mt-0.5 truncate text-lg font-semibold text-zinc-50">
              {heading}
            </h2>
          </div>
          <button
            type="button"
            className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
            aria-label="Close player"
            onClick={onClose}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="bg-black">
          <video
            key={src}
            className="aspect-video max-h-[70vh] w-full"
            controls
            autoPlay
            preload="metadata"
            src={src}
          >
            Your browser cannot play this video.
          </video>
        </div>
        <p className="px-4 py-2 text-xs text-zinc-500">
          Streamed from your download folder via the local media server — not
          locals.com.
        </p>
      </div>
    </dialog>
  )
}

import { X } from 'lucide-react'
import { useEffect, useState } from 'react'

interface CreatePathModalProps {
  open: boolean
  onClose: () => void
  onSave: (title: string, description: string) => Promise<void>
  videoCount: number
  /** Pre-filled title when opening (e.g. “Persuasion — My custom path”). */
  initialTitle?: string
}

const HEADING_ID = 'create-path-dialog-title'

export function CreatePathModal({
  open,
  onClose,
  onSave,
  videoCount,
  initialTitle = '',
}: CreatePathModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setTitle(initialTitle.trim())
      setDescription('')
      setError(null)
      setSaving(false)
    }
  }, [open, initialTitle])

  if (!open) return null

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const t = title.trim()
    if (!t) {
      setError('Please enter a title.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSave(t, description.trim())
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

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
        aria-labelledby={HEADING_ID}
        className="relative w-full max-w-md rounded-xl border border-zinc-600 bg-zinc-900 p-6 shadow-xl"
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
        <h2 id={HEADING_ID} className="text-lg font-semibold text-zinc-100">
          Create learning path
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          Save the current filtered list ({videoCount} video
          {videoCount === 1 ? '' : 's'}) as an ordered path.
        </p>
        <form className="mt-4 space-y-4" onSubmit={(e) => void handleSubmit(e)}>
          <div>
            <label htmlFor="create-path-title" className="text-sm text-zinc-400">
              Title
            </label>
            <input
              id="create-path-title"
              className="mt-1 w-full rounded-lg border border-zinc-600 bg-zinc-950 px-3 py-2 text-zinc-100 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Persuasion basics"
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="create-path-desc" className="text-sm text-zinc-400">
              Description (optional)
            </label>
            <textarea
              id="create-path-desc"
              rows={3}
              className="mt-1 w-full resize-y rounded-lg border border-zinc-600 bg-zinc-950 px-3 py-2 text-zinc-100 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this path covers…"
            />
          </div>
          {error ? (
            <p className="text-sm text-red-400" role="alert">
              {error}
            </p>
          ) : null}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              className="rounded-lg px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-800"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || videoCount === 0}
              className="rounded-lg bg-violet-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save path'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

import { CircleHelp, Search } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'

const DEBOUNCE_MS = 400

export function SearchBar() {
  const searchQuery = useTopicBrowserStore((s) => s.searchQuery)
  const setSearchQuery = useTopicBrowserStore((s) => s.setSearchQuery)

  const [draft, setDraft] = useState(searchQuery)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setDraft(searchQuery)
  }, [searchQuery])

  const flush = useCallback(
    (value: string) => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
      setSearchQuery(value.trim())
    },
    [setSearchQuery],
  )

  const schedule = useCallback(
    (value: string) => {
      setDraft(value)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        setSearchQuery(value.trim())
        timerRef.current = null
      }, DEBOUNCE_MS)
    },
    [setSearchQuery],
  )

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    },
    [],
  )

  return (
    <div className="w-full max-w-xl">
      <div className="flex items-center gap-2 rounded-lg border border-zinc-600 bg-zinc-900/80 px-3 py-2 shadow-inner focus-within:border-violet-500/60 focus-within:ring-1 focus-within:ring-violet-500/40">
        <Search className="h-5 w-5 shrink-0 text-zinc-500" aria-hidden />
        <input
          type="search"
          className="min-w-0 flex-1 bg-transparent text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
          placeholder="Search videos by title, topic, or cluster…"
          value={draft}
          onChange={(e) => schedule(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              flush(draft)
            }
          }}
          aria-label="Search videos"
        />
        <button
          type="button"
          className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
          onClick={() => flush(draft)}
          title="Search"
          aria-label="Run search"
        >
          <Search className="h-5 w-5" />
        </button>
      </div>
      <div className="mt-1.5 flex items-start gap-2 text-xs text-zinc-500">
        <span>Results update as you type.</span>
        <span
          className="group relative inline-flex items-center"
          title="Choose a topic or cluster and use search to refine the video list."
        >
          <CircleHelp className="h-3.5 w-3.5 cursor-help text-zinc-600 group-hover:text-zinc-400" />
          <span className="sr-only">
            Choose a topic or cluster and use search to refine the video list.
          </span>
        </span>
      </div>
    </div>
  )
}

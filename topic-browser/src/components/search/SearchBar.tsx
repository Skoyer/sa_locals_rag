import { CircleHelp, Search } from 'lucide-react'
import { useCallback } from 'react'

import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'

export function SearchBar() {
  const searchQuery = useTopicBrowserStore((s) => s.searchQuery)
  const setSearchQuery = useTopicBrowserStore((s) => s.setSearchQuery)

  const flush = useCallback(() => {
    const q = useTopicBrowserStore.getState().searchQuery.trim()
    setSearchQuery(q)
  }, [setSearchQuery])

  return (
    <div className="w-full max-w-xl">
      <div className="flex items-center gap-2 rounded-lg border border-zinc-600 bg-zinc-900/80 px-3 py-2 shadow-inner focus-within:border-violet-500/60 focus-within:ring-1 focus-within:ring-violet-500/40">
        <Search className="h-5 w-5 shrink-0 text-zinc-500" aria-hidden />
        <input
          type="search"
          className="min-w-0 flex-1 bg-transparent text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
          placeholder="Search videos by title, topic, or cluster…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              flush()
            }
          }}
          aria-label="Search videos"
        />
        <button
          type="button"
          className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
          onClick={flush}
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

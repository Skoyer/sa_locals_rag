import { Check } from 'lucide-react'

import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'

export function TopicList() {
  const topics = useTopicBrowserStore((s) => s.allTopics)
  const selectedTopicIds = useTopicBrowserStore((s) => s.selectedTopicIds)
  const setSelectedTopicIds = useTopicBrowserStore((s) => s.setSelectedTopicIds)

  return (
    <div>
      <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
        Topics
      </h2>
      <p className="mt-1 text-xs leading-snug text-zinc-500">
        Browse by curated categories (from topic tags on each video).
      </p>
      <ul className="mt-3 max-h-[min(40vh,320px)] space-y-1 overflow-y-auto pr-1">
        {topics.map((t) => {
          const selected = selectedTopicIds.includes(t.id)
          return (
            <li key={t.id}>
              <button
                type="button"
                onClick={() =>
                  setSelectedTopicIds(selected ? [] : [t.id])
                }
                className={`flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  selected
                    ? 'border-violet-500/60 bg-violet-950/50 text-zinc-50'
                    : 'border-transparent bg-zinc-900/40 text-zinc-300 hover:border-zinc-600 hover:bg-zinc-800/80'
                }`}
              >
                <span className="min-w-0 truncate">{t.name}</span>
                <span className="flex shrink-0 items-center gap-1.5 text-xs text-zinc-500">
                  ({t.videoCount})
                  {selected ? (
                    <Check className="h-3.5 w-3.5 text-violet-400" aria-hidden />
                  ) : null}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

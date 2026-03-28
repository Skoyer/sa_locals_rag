import { useEffect, useState } from 'react'

import { AppLayout } from './components/layout/AppLayout'
import { normalizeLessons } from './data/normalize'
import { useTopicBrowserStore } from './store/useTopicBrowserStore'
import type { LessonRaw } from './types'

export default function App() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const hydrate = useTopicBrowserStore((s) => s.hydrate)

  useEffect(() => {
    let cancelled = false
    fetch('/lessons.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<LessonRaw[]>
      })
      .then((raw) => {
        if (cancelled) return
        hydrate(normalizeLessons(raw))
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : String(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [hydrate])

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 p-8 text-red-400">
        <p className="font-medium">Failed to load lessons</p>
        <p className="mt-2 text-sm text-zinc-500">{error}</p>
        <p className="mt-4 text-sm text-zinc-400">
          Run the pipeline export:{' '}
          <code className="rounded bg-zinc-900 px-1.5 py-0.5 text-zinc-300">
            python -m web.summary_page
          </code>{' '}
          from the repo root to generate{' '}
          <code className="rounded bg-zinc-900 px-1.5 py-0.5 text-zinc-300">
            public/lessons.json
          </code>
          .
        </p>
      </div>
    )
  }

  return <AppLayout loading={loading} />
}

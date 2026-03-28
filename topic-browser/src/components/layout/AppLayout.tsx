import { ActiveFiltersBar } from '../filters/ActiveFiltersBar'
import { SearchBar } from '../search/SearchBar'
import { ClusterList } from '../sidebar/ClusterList'
import { TopicList } from '../sidebar/TopicList'
import { VideoGrid } from '../videos/VideoGrid'

interface AppLayoutProps {
  loading: boolean
}

export function AppLayout({ loading }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="text-left">
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">
              Topic Browser
            </h1>
            <p className="mt-1 max-w-xl text-sm text-zinc-500">
              Topics are curated tags; clusters are auto-discovered themes.
            </p>
          </div>
          <SearchBar />
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[minmax(240px,280px)_1fr]">
        <aside className="space-y-8 lg:sticky lg:top-6 lg:self-start">
          <TopicList />
          <ClusterList />
        </aside>

        <main className="min-w-0 space-y-6">
          <ActiveFiltersBar />
          <div>
            <h2 className="mb-3 text-lg font-medium text-zinc-200">Videos</h2>
            <VideoGrid loading={loading} />
          </div>
        </main>
      </div>
    </div>
  )
}

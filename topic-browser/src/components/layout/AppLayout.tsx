import { useEffect, useState } from 'react'

import { useTopicBrowserStore } from '../../store/useTopicBrowserStore'
import { ActiveFiltersBar } from '../filters/ActiveFiltersBar'
import { LearningPathsTab } from '../paths/LearningPathsTab'
import { PathPreviewBanner } from '../paths/PathPreviewBanner'
import { PathProgressBar } from '../videos/PathProgressBar'
import { SearchBar } from '../search/SearchBar'
import { ClusterList } from '../sidebar/ClusterList'
import { TopicList } from '../sidebar/TopicList'
import { VideoGrid } from '../videos/VideoGrid'
import { AuthHeader } from './AuthHeader'

type MainTab = 'videos' | 'paths'

interface AppLayoutProps {
  loading: boolean
  activeTab: MainTab
  onTabChange: (tab: MainTab) => void
}

export function AppLayout({ loading, activeTab, onTabChange }: AppLayoutProps) {
  const clearPathFilter = useTopicBrowserStore((s) => s.clearPathFilter)
  const [pathSavedToast, setPathSavedToast] = useState<string | null>(null)

  useEffect(() => {
    if (!pathSavedToast) return
    const t = window.setTimeout(() => setPathSavedToast(null), 4500)
    return () => clearTimeout(t)
  }, [pathSavedToast])

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0 flex-1 text-left">
              <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">
                Topic Browser
              </h1>
              <p className="mt-1 max-w-xl text-sm text-zinc-500">
                Bite-sized lessons from Scott Adams&apos; library.
              </p>
            </div>
            <div className="w-full min-w-0 flex-1 lg:max-w-xl">
              <SearchBar />
            </div>
            <div className="flex w-full max-w-md shrink-0 justify-end lg:w-auto lg:max-w-[min(100%,22rem)] lg:pt-1">
              <AuthHeader />
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl border-b border-zinc-800 px-4">
        <nav className="flex gap-1" aria-label="Main sections">
          <button
            type="button"
            className={`border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'paths'
                ? 'border-violet-500 text-zinc-100'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            }`}
            onClick={() => onTabChange('paths')}
          >
            Learning Paths
          </button>
          <button
            type="button"
            className={`border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'videos'
                ? 'border-violet-500 text-zinc-100'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            }`}
            onClick={() => onTabChange('videos')}
          >
            Videos
          </button>
        </nav>
      </div>

      <div
        className={`mx-auto grid max-w-7xl gap-6 px-4 py-6 ${
          activeTab === 'videos'
            ? 'lg:grid-cols-[minmax(240px,280px)_1fr]'
            : ''
        }`}
      >
        {activeTab === 'videos' ? (
          <aside className="space-y-8 lg:sticky lg:top-6 lg:self-start">
            <TopicList />
            <ClusterList />
          </aside>
        ) : null}

        <main className="min-w-0 space-y-6">
          {pathSavedToast ? (
            <p
              className="rounded-lg border border-emerald-800/60 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-200"
              role="status"
            >
              {pathSavedToast}
            </p>
          ) : null}
          {activeTab === 'videos' ? (
            <>
              <div>
                <h2 className="mb-3 text-lg font-medium text-zinc-200">Videos</h2>
                <PathProgressBar
                  onBackToPaths={() => {
                    clearPathFilter()
                    onTabChange('paths')
                  }}
                  onTabChange={onTabChange}
                  onPathSaved={() =>
                    setPathSavedToast(
                      'Path saved. You can find it under ‘Your paths’.',
                    )
                  }
                />
              </div>
              <PathPreviewBanner />
              <ActiveFiltersBar />
              <VideoGrid loading={loading} />
            </>
          ) : (
            <LearningPathsTab
              onViewPathInGrid={(videoIds, title, pathId, options) => {
                useTopicBrowserStore.getState().setPathFilter(
                  videoIds,
                  title,
                  pathId ?? null,
                  options?.preview,
                  {
                    defaultSaveTitle: options?.defaultSaveTitle ?? null,
                  },
                )
                onTabChange('videos')
              }}
              onTabChange={onTabChange}
            />
          )}
        </main>
      </div>
    </div>
  )
}

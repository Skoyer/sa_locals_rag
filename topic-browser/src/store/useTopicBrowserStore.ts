import { create } from 'zustand'

import type { Cluster, Topic, Video } from '../types'

interface TopicBrowserState {
  allTopics: Topic[]
  allClusters: Cluster[]
  allVideos: Video[]
  /** Empty = no topic filter. Multiple ids = video must match at least one topic. */
  selectedTopicIds: string[]
  /**
   * Interest-tile filter: match raw `topic_buckets` against these slugs (cleared when sidebar topics used).
   */
  interestBucketSlugs: string[] | null
  selectedClusterId: number | null
  searchQuery: string
  /** When set, grid shows only these ids (in order), intersected with topic/cluster/search filters. */
  pathFilterVideoIds: number[] | null
  pathFilterTitle: string | null
  /** Supabase featured/user path id when path is active (for progress UI). */
  activePathId: string | null
  /** True when path filter is “review this set” without having saved a user path yet. */
  pathPreviewMode: boolean
  /** Default title for “Save as my custom path” modal (e.g. “Persuasion — My custom path”). */
  reviewDraftDefaultTitle: string | null
  hydrate: (data: {
    topics: Topic[]
    clusters: Cluster[]
    videos: Video[]
  }) => void
  setSelectedTopicIds: (ids: string[]) => void
  setInterestBucketSlugs: (slugs: string[] | null) => void
  setSelectedClusterId: (id: number | null) => void
  setSearchQuery: (q: string) => void
  setPathFilter: (
    videoIds: number[] | null,
    title?: string | null,
    activePathId?: string | null,
    preview?: boolean,
    options?: { defaultSaveTitle?: string | null },
  ) => void
  removeVideoFromPathDraft: (videoId: number) => void
  addVideoToPathDraft: (videoId: number) => void
  clearTopic: () => void
  clearCluster: () => void
  clearSearch: () => void
  clearPathFilter: () => void
  clearAllFilters: () => void
}

export const useTopicBrowserStore = create<TopicBrowserState>((set, get) => ({
  allTopics: [],
  allClusters: [],
  allVideos: [],
  selectedTopicIds: [],
  interestBucketSlugs: null,
  selectedClusterId: null,
  searchQuery: '',
  pathFilterVideoIds: null,
  pathFilterTitle: null,
  activePathId: null,
  pathPreviewMode: false,
  reviewDraftDefaultTitle: null,
  hydrate: (data) =>
    set({
      allTopics: data.topics,
      allClusters: data.clusters,
      allVideos: data.videos,
      selectedTopicIds: [],
      interestBucketSlugs: null,
      selectedClusterId: null,
      searchQuery: '',
      pathFilterVideoIds: null,
      pathFilterTitle: null,
      activePathId: null,
      pathPreviewMode: false,
      reviewDraftDefaultTitle: null,
    }),
  setSelectedTopicIds: (ids) =>
    set({ selectedTopicIds: ids, interestBucketSlugs: null }),
  setInterestBucketSlugs: (slugs) =>
    set({ interestBucketSlugs: slugs, selectedTopicIds: [] }),
  setSelectedClusterId: (id) => set({ selectedClusterId: id }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  setPathFilter: (videoIds, title, activePathId, preview, options) => {
    if (preview === true && videoIds && videoIds.length === 0) {
      set({
        pathFilterVideoIds: [],
        pathFilterTitle: title ?? null,
        activePathId: null,
        pathPreviewMode: true,
        reviewDraftDefaultTitle:
          options?.defaultSaveTitle !== undefined
            ? options.defaultSaveTitle
            : get().reviewDraftDefaultTitle,
      })
      return
    }
    if (videoIds && videoIds.length > 0) {
      set({
        pathFilterVideoIds: videoIds,
        pathFilterTitle: title ?? null,
        activePathId: activePathId ?? null,
        pathPreviewMode: preview === true,
        reviewDraftDefaultTitle:
          preview === true
            ? (options?.defaultSaveTitle ?? null)
            : null,
        selectedTopicIds: [],
        interestBucketSlugs: null,
        selectedClusterId: null,
        searchQuery: '',
      })
    } else {
      set({
        pathFilterVideoIds: null,
        pathFilterTitle: null,
        activePathId: null,
        pathPreviewMode: false,
        reviewDraftDefaultTitle: null,
      })
    }
  },
  removeVideoFromPathDraft: (videoId) =>
    set((state) => {
      if (!state.pathPreviewMode || state.pathFilterVideoIds === null) {
        return state
      }
      const next = state.pathFilterVideoIds.filter((id) => id !== videoId)
      return { pathFilterVideoIds: next }
    }),
  addVideoToPathDraft: (videoId) =>
    set((state) => {
      if (!state.pathPreviewMode || state.pathFilterVideoIds === null) {
        return state
      }
      if (state.pathFilterVideoIds.includes(videoId)) return state
      return { pathFilterVideoIds: [...state.pathFilterVideoIds, videoId] }
    }),
  clearTopic: () => set({ selectedTopicIds: [], interestBucketSlugs: null }),
  clearCluster: () => set({ selectedClusterId: null }),
  clearSearch: () => set({ searchQuery: '' }),
  clearPathFilter: () =>
    set({
      pathFilterVideoIds: null,
      pathFilterTitle: null,
      activePathId: null,
      pathPreviewMode: false,
      reviewDraftDefaultTitle: null,
    }),
  clearAllFilters: () =>
    set({
      selectedTopicIds: [],
      interestBucketSlugs: null,
      selectedClusterId: null,
      searchQuery: '',
      pathFilterVideoIds: null,
      pathFilterTitle: null,
      activePathId: null,
      pathPreviewMode: false,
      reviewDraftDefaultTitle: null,
    }),
}))

/** Pure helper; do not pass to `useTopicBrowserStore(fn)` — fn must return stable refs; this returns a new array each call. */
export function selectSelectedTopics(state: TopicBrowserState): Topic[] {
  return state.selectedTopicIds
    .map((id) => state.allTopics.find((t) => t.id === id))
    .filter((t): t is Topic => t != null)
}

export function selectSelectedCluster(
  state: TopicBrowserState,
): Cluster | undefined {
  if (state.selectedClusterId == null) return undefined
  return state.allClusters.find((c) => c.id === state.selectedClusterId)
}

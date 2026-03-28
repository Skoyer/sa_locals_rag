import { create } from 'zustand'

import type { Cluster, Topic, Video } from '../types'

interface TopicBrowserState {
  allTopics: Topic[]
  allClusters: Cluster[]
  allVideos: Video[]
  selectedTopicId: string | null
  selectedClusterId: number | null
  searchQuery: string
  hydrate: (data: {
    topics: Topic[]
    clusters: Cluster[]
    videos: Video[]
  }) => void
  setSelectedTopicId: (id: string | null) => void
  setSelectedClusterId: (id: number | null) => void
  setSearchQuery: (q: string) => void
  clearTopic: () => void
  clearCluster: () => void
  clearSearch: () => void
  clearAllFilters: () => void
}

export const useTopicBrowserStore = create<TopicBrowserState>((set) => ({
  allTopics: [],
  allClusters: [],
  allVideos: [],
  selectedTopicId: null,
  selectedClusterId: null,
  searchQuery: '',
  hydrate: (data) =>
    set({
      allTopics: data.topics,
      allClusters: data.clusters,
      allVideos: data.videos,
    }),
  setSelectedTopicId: (id) => set({ selectedTopicId: id }),
  setSelectedClusterId: (id) => set({ selectedClusterId: id }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  clearTopic: () => set({ selectedTopicId: null }),
  clearCluster: () => set({ selectedClusterId: null }),
  clearSearch: () => set({ searchQuery: '' }),
  clearAllFilters: () =>
    set({
      selectedTopicId: null,
      selectedClusterId: null,
      searchQuery: '',
    }),
}))

export function selectSelectedTopic(
  state: TopicBrowserState,
): Topic | undefined {
  if (!state.selectedTopicId) return undefined
  return state.allTopics.find((t) => t.id === state.selectedTopicId)
}

export function selectSelectedCluster(
  state: TopicBrowserState,
): Cluster | undefined {
  if (state.selectedClusterId == null) return undefined
  return state.allClusters.find((c) => c.id === state.selectedClusterId)
}

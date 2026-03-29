import type { Video } from '../types'

import { sortVideosForInterestPath } from './interestStarterPath'

export const WATCH_EVERYTHING_TITLE = "Watch Everything You Haven't Seen"
export const WATCH_EVERYTHING_DESCRIPTION =
  'Automatically updated list of all remaining lessons.'
export const LOCAL_WATCH_EVERYTHING_PATH_ID = 'local-watch-everything'

/** Topic bucket groups used to interleave (broad families). */
const BUCKET_GROUPS: string[][] = [
  ['persuasion', 'communication', 'compliments'],
  ['cognitive_bias', 'critical_thinking', 'self_programming'],
  ['energy_management', 'diet', 'health'],
  ['creativity', 'personal_brand', 'career'],
  ['mindfulness', 'stress', 'emotional_intelligence'],
]

function norm(s: string): string {
  return s.trim().toLowerCase()
}

function groupKeyForVideo(v: Video): string {
  const buckets = (v.topic_buckets ?? []).map(norm)
  for (const g of BUCKET_GROUPS) {
    for (const b of buckets) {
      if (g.some((x) => norm(x) === b)) return g[0]
    }
  }
  const first = buckets[0]
  return first || 'other'
}

/**
 * Remaining unwatched videos in a smart order: per-group sort, then round-robin
 * across groups to avoid long runs of one topic.
 */
export function orderWatchEverythingVideos(
  remaining: Video[],
): number[] {
  if (remaining.length === 0) return []
  const byGroup = new Map<string, Video[]>()
  for (const v of remaining) {
    const k = groupKeyForVideo(v)
    const list = byGroup.get(k) ?? []
    list.push(v)
    byGroup.set(k, list)
  }
  for (const [k, list] of byGroup) {
    byGroup.set(k, sortVideosForInterestPath(list))
  }
  const keys = [...byGroup.keys()].sort((a, b) => a.localeCompare(b))
  const out: number[] = []
  let round = 0
  let added = true
  while (added) {
    added = false
    for (const k of keys) {
      const list = byGroup.get(k) ?? []
      if (round < list.length) {
        out.push(list[round].id)
        added = true
      }
    }
    round++
  }
  return out
}

export function remainingUnwatchedVideos(
  allVideos: Video[],
  watchedIds: Set<number>,
): Video[] {
  return allVideos.filter((v) => !watchedIds.has(v.id))
}

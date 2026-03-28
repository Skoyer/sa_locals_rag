import type {
  Cluster,
  LessonRaw,
  NormalizeResult,
  Topic,
  Video,
} from '../types'

/** Stable id from bucket label (topic_browser v1 does not use topic_tree.json). */
export function slugifyTopicId(name: string): string {
  const s = name.trim().toLowerCase().replace(/\s+/g, '-')
  return s.replace(/[^a-z0-9-]/g, '') || 'topic'
}

/**
 * Topics and clusters are derived only from `topic_buckets` and `cluster_id` so
 * sidebar counts always match the video grid.
 */
export function normalizeLessons(raw: LessonRaw[]): NormalizeResult {
  const topicCounts = new Map<string, number>()
  const clusterMeta = new Map<
    number,
    { count: number; name: string }
  >()

  for (const L of raw) {
    for (const b of L.topic_buckets || []) {
      const name = b.trim()
      if (!name) continue
      topicCounts.set(name, (topicCounts.get(name) ?? 0) + 1)
    }
    const cid = L.cluster_id
    if (cid == null) continue
    const label = (L.cluster_name || '').trim() || `Cluster ${cid}`
    const prev = clusterMeta.get(cid)
    if (!prev) {
      clusterMeta.set(cid, { count: 1, name: label })
    } else {
      clusterMeta.set(cid, {
        count: prev.count + 1,
        name: prev.name || label,
      })
    }
  }

  const topicById = new Map<string, Topic>()
  for (const [name, count] of topicCounts) {
    if (count < 1) continue
    const id = slugifyTopicId(name)
    topicById.set(id, { id, name, videoCount: count })
  }

  const topics = [...topicById.values()].sort((a, b) =>
    a.name.localeCompare(b.name),
  )

  const clusters: Cluster[] = [...clusterMeta.entries()]
    .map(([id, { count, name }]) => ({
      id,
      name,
      videoCount: count,
    }))
    .sort((a, b) => a.id - b.id)

  const clusterById = new Map<number, Cluster>(
    clusters.map((c) => [c.id, c]),
  )

  const videos: Video[] = raw.map((L) => {
    const seen = new Set<string>()
    const videoTopics: Topic[] = []
    for (const b of L.topic_buckets || []) {
      const name = b.trim()
      if (!name) continue
      const tid = slugifyTopicId(name)
      const t = topicById.get(tid)
      if (t && !seen.has(t.id)) {
        seen.add(t.id)
        videoTopics.push(t)
      }
    }
    videoTopics.sort((a, b) => a.name.localeCompare(b.name))

    const cluster =
      L.cluster_id != null ? clusterById.get(L.cluster_id) ?? null : null

    return {
      ...L,
      id: L.transcript_id,
      topics: videoTopics,
      cluster,
    }
  })

  return { topics, clusters, videos }
}

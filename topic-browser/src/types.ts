/**
 * Raw lesson row from `public/lessons.json` (same shape as `SA_LESSONS_DATA.lessons`
 * from `web/summary_page.py`).
 *
 * Note: `data/topic_tree.json` is not used by Topic Browser v1 — it is reserved for a
 * future “Learning paths” feature only.
 */
export interface LessonRaw {
  transcript_id: number
  url: string
  title: string
  /** Short display title from `scripts/generate_short_titles.py` (optional until generated). */
  short_title?: string
  summary_text: string
  core_lesson: string
  key_concepts: string[]
  difficulty: string
  primary_topics: string[]
  prerequisites: string[]
  builds_toward: string[]
  cluster_id: number | null
  cluster_name: string
  wordcloud_path: string
  topic_buckets: string[]
  is_persuasion_focused: boolean | null
}

export interface Topic {
  id: string
  name: string
  videoCount: number
}

export interface Cluster {
  id: number
  name: string
  videoCount: number
}

/** Normalized video for the UI: one cluster per lesson (matches export). */
export interface Video extends LessonRaw {
  /** Same as `transcript_id`; convenient for keys and filters. */
  id: number
  topics: Topic[]
  cluster: Cluster | null
}

export interface NormalizeResult {
  topics: Topic[]
  clusters: Cluster[]
  videos: Video[]
}

export interface LearningPathBase {
  id: string
  title: string
  description?: string | null
  tags: string[]
  videoIds: number[]
  createdAt: string
}

export interface FeaturedLearningPath extends LearningPathBase {
  kind: 'featured'
}

export interface UserLearningPath extends LearningPathBase {
  kind: 'user'
  updatedAt: string
}

export interface UserProfile {
  id: string
  displayName?: string | null
  createdAt: string
}

export interface VideoProgress {
  userId: string
  videoId: number
  completedAt: string
}

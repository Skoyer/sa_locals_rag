import { slugifyTopicId } from './normalize'

/** Six landing-page interests → topic_bucket strings (match `lessons.json` topic_buckets). */
export type InterestId =
  | 'thinking'
  | 'persuasion'
  | 'energy'
  | 'creativity'
  | 'career'
  | 'health'

export const INTEREST_TILES: {
  id: InterestId
  label: string
  icon: string
  bucketSlugs: string[]
}[] = [
  {
    id: 'thinking',
    label: 'Thinking',
    icon: '🧠',
    bucketSlugs: ['cognitive_bias', 'critical_thinking', 'self_programming'],
  },
  {
    id: 'persuasion',
    label: 'Persuasion',
    icon: '💬',
    bucketSlugs: ['persuasion', 'communication', 'compliments'],
  },
  {
    id: 'energy',
    label: 'Energy',
    icon: '⚡',
    bucketSlugs: ['energy_management', 'diet', 'health'],
  },
  {
    id: 'creativity',
    label: 'Creativity',
    icon: '🎨',
    bucketSlugs: ['creativity', 'personal_brand'],
  },
  {
    id: 'career',
    label: 'Career',
    icon: '💼',
    bucketSlugs: ['career', 'personal_brand'],
  },
  {
    id: 'health',
    label: 'Health',
    icon: '❤️',
    bucketSlugs: ['health', 'mindfulness', 'stress', 'emotional_intelligence'],
  },
]

function normBucket(s: string): string {
  return s.trim().toLowerCase()
}

/** Topic ids that exist in the catalog for this interest’s bucket slugs. */
export function topicIdsForInterestBuckets(
  bucketSlugs: string[],
  existingTopicIds: Set<string>,
): string[] {
  const ids = new Set<string>()
  for (const raw of bucketSlugs) {
    const id = slugifyTopicId(raw)
    if (existingTopicIds.has(id)) ids.add(id)
  }
  return [...ids]
}

/** Synthetic path id when starting a computed interest path without a Supabase row. */
export function localInterestPathId(interestId: InterestId): string {
  return `local-interest-${interestId}`
}

/** Video matches interest if any raw topic_bucket matches configured slugs. */
export function videoMatchesInterestBuckets(
  topicBuckets: string[] | undefined | null,
  bucketSlugs: string[],
): boolean {
  const buckets = topicBuckets ?? []
  const want = new Set(bucketSlugs.map(normBucket))
  return buckets.some((b) =>
    want.has(normBucket(typeof b === 'string' ? b : String(b))),
  )
}

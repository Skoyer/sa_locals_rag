import type { InterestId } from '../../data/interestBuckets'
import type { FeaturedLearningPath } from '../../types'

/** Pick a featured path card to show for an interest (by title keywords). */
export function featuredPathForInterest(
  interestId: InterestId,
  paths: FeaturedLearningPath[],
): FeaturedLearningPath | null {
  if (paths.length === 0) return null

  const patterns: Record<InterestId, RegExp[]> = {
    thinking: [/clear\s*thinking/i, /thinking/i],
    persuasion: [/persuasion/i, /influence/i],
    energy: [/energy/i, /health/i],
    creativity: [/creativity/i, /career/i],
    career: [/career/i, /creativity/i],
    health: [/health/i, /energy/i, /emotional/i],
  }

  const regs = patterns[interestId]
  for (const re of regs) {
    const hit = paths.find((p) => re.test(p.title))
    if (hit) return hit
  }
  return paths[0]
}

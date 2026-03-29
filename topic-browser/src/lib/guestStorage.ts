import type { UserLearningPath, VideoProgress } from '../types'

export const GUEST_ID_KEY = 'tb_guest_id'
const GUEST_PATHS_KEY = 'tb_guest_paths'
const GUEST_PROGRESS_KEY = 'tb_guest_progress'

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback
  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export function getOrCreateGuestId(): string {
  try {
    const existing = localStorage.getItem(GUEST_ID_KEY)
    if (existing && existing.length > 0) return existing
    const id = crypto.randomUUID()
    localStorage.setItem(GUEST_ID_KEY, id)
    return id
  } catch {
    return `guest-${Math.random().toString(36).slice(2)}`
  }
}

export function loadGuestPaths(): UserLearningPath[] {
  try {
    const raw = localStorage.getItem(GUEST_PATHS_KEY)
    const parsed = safeParse<unknown>(raw, [])
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (p): p is UserLearningPath =>
        typeof p === 'object' &&
        p != null &&
        (p as UserLearningPath).kind === 'user' &&
        typeof (p as UserLearningPath).id === 'string',
    )
  } catch {
    return []
  }
}

export function saveGuestPaths(paths: UserLearningPath[]): void {
  try {
    localStorage.setItem(GUEST_PATHS_KEY, JSON.stringify(paths))
  } catch {
    /* ignore quota */
  }
}

export function loadGuestProgress(guestId: string): VideoProgress[] {
  try {
    const raw = localStorage.getItem(GUEST_PROGRESS_KEY)
    const parsed = safeParse<unknown>(raw, [])
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter(
        (row): row is VideoProgress =>
          typeof row === 'object' &&
          row != null &&
          typeof (row as VideoProgress).videoId === 'number' &&
          (row as VideoProgress).userId === guestId,
      )
      .map((row) => ({
        userId: row.userId,
        videoId: row.videoId,
        completedAt: row.completedAt,
      }))
  } catch {
    return []
  }
}

export function saveGuestProgress(_guestId: string, rows: VideoProgress[]): void {
  try {
    localStorage.setItem(GUEST_PROGRESS_KEY, JSON.stringify(rows))
  } catch {
    /* ignore */
  }
}

export function clearGuestData(): void {
  try {
    localStorage.removeItem(GUEST_PATHS_KEY)
    localStorage.removeItem(GUEST_PROGRESS_KEY)
  } catch {
    /* ignore */
  }
}

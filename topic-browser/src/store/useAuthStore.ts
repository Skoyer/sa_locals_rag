import { create } from 'zustand'
import type { AuthError } from '@supabase/supabase-js'

import {
  clearGuestData,
  getOrCreateGuestId,
  GUEST_ID_KEY,
  loadGuestPaths,
  loadGuestProgress,
  saveGuestPaths,
  saveGuestProgress,
} from '../lib/guestStorage'
import { isSupabaseConfigured, supabase } from '../lib/supabaseClient'
import type { UserLearningPath, UserProfile, VideoProgress } from '../types'

/** Avoid overlapping initFromSession runs (listener + startup, TOKEN_REFRESHED bursts). */
let initFromSessionInFlight = false
/** If auth fires again while a run is in flight (e.g. magic link INITIAL_SESSION), run once more after. */
let initFromSessionPending = false

function loadGuestState() {
  const guestId = getOrCreateGuestId()
  return {
    guestId,
    guestPaths: loadGuestPaths(),
    guestProgress: loadGuestProgress(guestId),
  }
}

function isRateLimitedOtpError(error: AuthError): boolean {
  const msg = error.message?.toLowerCase() ?? ''
  const code = error.code?.toLowerCase() ?? ''
  return (
    code === 'over_email_send_rate_limit' ||
    msg.includes('rate limit') ||
    msg.includes('email rate') ||
    msg.includes('too many requests') ||
    (typeof error === 'object' &&
      error !== null &&
      'status' in error &&
      (error as { status?: number }).status === 429)
  )
}

function formatSignInOtpError(error: AuthError): string {
  if (isRateLimitedOtpError(error)) {
    return (
      'Too many sign-in emails were sent. Wait several minutes before trying again, ' +
      'or open the link from an email you already received if it is still valid.'
    )
  }
  return (
    error.message ||
    'We couldn’t send an email right now, please try again in a few minutes.'
  )
}

async function mergeGuestIntoAccount(userId: string): Promise<void> {
  if (!isSupabaseConfigured) return
  const guestPaths = loadGuestPaths()
  const gid = localStorage.getItem(GUEST_ID_KEY)
  const guestProgressRows = gid ? loadGuestProgress(gid) : []
  if (guestPaths.length === 0 && guestProgressRows.length === 0) return

  for (const p of guestPaths) {
    const { error } = await supabase.from('user_learning_paths').insert({
      user_id: userId,
      title: p.title,
      description: p.description ?? null,
      tags: p.tags ?? [],
      video_ids: p.videoIds,
    })
    if (error) {
      console.error('mergeGuestIntoAccount path:', error.message)
    }
  }

  for (const row of guestProgressRows) {
    const { data: existing } = await supabase
      .from('video_progress')
      .select('video_id')
      .eq('user_id', userId)
      .eq('video_id', row.videoId)
      .maybeSingle()
    if (existing) continue
    const { error } = await supabase.from('video_progress').insert({
      user_id: userId,
      video_id: row.videoId,
    })
    if (error) {
      console.error('mergeGuestIntoAccount progress:', error.message)
    }
  }

  clearGuestData()
}

interface AuthState {
  user: { id: string; email?: string | null } | null
  profile: UserProfile | null
  userPaths: UserLearningPath[]
  progress: VideoProgress[]
  /** Browser-only identity when not signed in (persisted in localStorage). */
  guestId: string | null
  guestPaths: UserLearningPath[]
  guestProgress: VideoProgress[]
  loading: boolean

  initFromSession: () => Promise<void>
  /** Magic link (OTP) — user completes sign-in via link in email. */
  sendMagicLink: (
    email: string,
  ) => Promise<{ ok: boolean; error?: string; rateLimited?: boolean }>
  signOut: () => Promise<void>
  toggleVideoWatched: (videoId: number) => Promise<void>
  saveUserPathFromVideoIds: (
    title: string,
    description: string | undefined,
    videoIds: number[],
  ) => Promise<{ ok: boolean; error?: string; pathId?: string }>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  profile: null,
  userPaths: [],
  progress: [],
  guestId: null,
  guestPaths: [],
  guestProgress: [],
  loading: true,

  initFromSession: async () => {
    if (!isSupabaseConfigured) {
      const g = loadGuestState()
      set({
        user: null,
        profile: null,
        userPaths: [],
        progress: [],
        guestId: g.guestId,
        guestPaths: g.guestPaths,
        guestProgress: g.guestProgress,
        loading: false,
      })
      return
    }

    if (initFromSessionInFlight) {
      initFromSessionPending = true
      return
    }
    initFromSessionInFlight = true

    try {
      set({ loading: true })
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session?.user) {
        const g = loadGuestState()
        set({
          user: null,
          profile: null,
          userPaths: [],
          progress: [],
          guestId: g.guestId,
          guestPaths: g.guestPaths,
          guestProgress: g.guestProgress,
          loading: false,
        })
        return
      }

      const user = { id: session.user.id, email: session.user.email }

      const profileRes = await supabase
        .from('profiles')
        .select('*')
        .eq('id', user.id)
        .maybeSingle()

      let profileRow = profileRes.data as {
        id: string
        display_name: string | null
        created_at: string
      } | null

      if (!profileRow && !profileRes.error) {
        const display =
          (session.user.user_metadata?.full_name as string | undefined) ??
          session.user.email ??
          'Learner'
        const ins = await supabase
          .from('profiles')
          .insert({ id: user.id, display_name: display })
          .select('*')
          .maybeSingle()
        profileRow = ins.data as typeof profileRow
      }

      if (!profileRow) {
        set({
          user,
          profile: null,
          userPaths: [],
          progress: [],
          guestId: null,
          guestPaths: [],
          guestProgress: [],
          loading: false,
        })
        return
      }

      await mergeGuestIntoAccount(user.id)

      const [pathsRes2, progressRes2] = await Promise.all([
        supabase
          .from('user_learning_paths')
          .select('*')
          .eq('user_id', user.id)
          .order('created_at', { ascending: true }),
        supabase.from('video_progress').select('*').eq('user_id', user.id),
      ])

      const paths = pathsRes2.data ?? []
      const progressRows = progressRes2.data ?? []

      const g = loadGuestState()

      set({
        user,
        profile: {
          id: profileRow.id,
          displayName: profileRow.display_name,
          createdAt: profileRow.created_at,
        },
        userPaths: paths.map(mapUserPathRow),
        progress: progressRows.map((r: VideoProgressRow) => ({
          userId: r.user_id,
          videoId: r.video_id,
          completedAt: r.completed_at,
        })),
        guestId: g.guestId,
        guestPaths: [],
        guestProgress: [],
        loading: false,
      })
    } finally {
      initFromSessionInFlight = false
      if (initFromSessionPending) {
        initFromSessionPending = false
        void get().initFromSession()
      }
    }
  },

  sendMagicLink: async (email) => {
    if (!isSupabaseConfigured) {
      return {
        ok: false,
        error:
          'Supabase is not configured (set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY).',
      }
    }
    const trimmed = email.trim()
    if (!trimmed) {
      return { ok: false, error: 'Enter your email address.' }
    }
    const { error } = await supabase.auth.signInWithOtp({
      email: trimmed,
      options: {
        shouldCreateUser: true,
        emailRedirectTo: `${window.location.origin}${window.location.pathname}`,
      },
    })
    if (error) {
      console.error('Supabase signInWithOtp:', error.message, error)
      return {
        ok: false,
        error: formatSignInOtpError(error),
        rateLimited: isRateLimitedOtpError(error),
      }
    }
    return { ok: true }
  },

  signOut: async () => {
    if (isSupabaseConfigured) {
      const { error } = await supabase.auth.signOut()
      if (error) console.error('Supabase signOut:', error.message)
    }
    const g = loadGuestState()
    set({
      user: null,
      profile: null,
      userPaths: [],
      progress: [],
      guestId: g.guestId,
      guestPaths: g.guestPaths,
      guestProgress: g.guestProgress,
    })
  },

  toggleVideoWatched: async (videoId) => {
    const { user, progress, guestId, guestProgress } = get()
    if (user) {
      const existing = progress.find((p) => p.videoId === videoId)
      if (existing) {
        await supabase
          .from('video_progress')
          .delete()
          .eq('user_id', user.id)
          .eq('video_id', videoId)
        set({ progress: progress.filter((p) => p.videoId !== videoId) })
      } else {
        const { data, error } = await supabase
          .from('video_progress')
          .insert({ user_id: user.id, video_id: videoId })
          .select('*')
          .single()

        if (error) {
          console.error('toggleVideoWatched insert:', error.message)
          return
        }
        if (data) {
          const row = data as VideoProgressRow
          set({
            progress: [
              ...progress,
              {
                userId: row.user_id,
                videoId: row.video_id,
                completedAt: row.completed_at,
              },
            ],
          })
        }
      }
      return
    }

    if (!guestId) return
    const existing = guestProgress.find((p) => p.videoId === videoId)
    if (existing) {
      const next = guestProgress.filter((p) => p.videoId !== videoId)
      saveGuestProgress(guestId, next)
      set({ guestProgress: next })
    } else {
      const row: VideoProgress = {
        userId: guestId,
        videoId,
        completedAt: new Date().toISOString(),
      }
      const next = [...guestProgress, row]
      saveGuestProgress(guestId, next)
      set({ guestProgress: next })
    }
  },

  saveUserPathFromVideoIds: async (title, description, videoIds) => {
    const { user, userPaths, guestId, guestPaths } = get()
    if (videoIds.length === 0) {
      return { ok: false, error: 'No videos selected.' }
    }

    if (user) {
      const { data, error } = await supabase
        .from('user_learning_paths')
        .insert({
          user_id: user.id,
          title,
          description: description ?? null,
          video_ids: videoIds,
        })
        .select('*')
        .single()

      if (error) {
        console.error('saveUserPathFromVideoIds:', error.message)
        return { ok: false, error: error.message }
      }

      if (data) {
        const row = data as UserPathRow
        set({
          userPaths: [...userPaths, mapUserPathRow(row)],
        })
        return { ok: true, pathId: row.id }
      }
      return { ok: true }
    }

    if (!guestId) {
      return { ok: false, error: 'Not signed in or no videos selected.' }
    }
    const now = new Date().toISOString()
    const path: UserLearningPath = {
      id: `guest-${crypto.randomUUID()}`,
      kind: 'user',
      title,
      description: description ?? null,
      tags: [],
      videoIds,
      createdAt: now,
      updatedAt: now,
    }
    const next = [...guestPaths, path]
    saveGuestPaths(next)
    set({ guestPaths: next })
    return { ok: true, pathId: path.id }
  },
}))

interface VideoProgressRow {
  user_id: string
  video_id: number
  completed_at: string
}

interface UserPathRow {
  id: string
  user_id: string
  title: string
  description: string | null
  tags: string[] | null
  video_ids: number[]
  created_at: string
  updated_at: string
}

function mapUserPathRow(p: UserPathRow): UserLearningPath {
  return {
    id: p.id,
    kind: 'user',
    title: p.title,
    description: p.description,
    tags: p.tags ?? [],
    videoIds: p.video_ids ?? [],
    createdAt: p.created_at,
    updatedAt: p.updated_at,
  }
}

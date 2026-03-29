import { Loader2, LogOut, Mail } from 'lucide-react'
import { useEffect, useState } from 'react'

import { isSupabaseConfigured } from '../../lib/supabaseClient'
import { useAuthStore } from '../../store/useAuthStore'

function initials(email: string | null | undefined): string {
  if (!email) return '?'
  const part = email.split('@')[0] ?? email
  if (part.length >= 2) return part.slice(0, 2).toUpperCase()
  return part.slice(0, 1).toUpperCase()
}

export function AuthHeader() {
  const user = useAuthStore((s) => s.user)
  const guestId = useAuthStore((s) => s.guestId)
  const profile = useAuthStore((s) => s.profile)
  const loading = useAuthStore((s) => s.loading)
  const signOut = useAuthStore((s) => s.signOut)
  const sendMagicLink = useAuthStore((s) => s.sendMagicLink)

  const [email, setEmail] = useState('')
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  /** Blocks repeat requests to avoid Supabase email rate limits. */
  const [cooldownSeconds, setCooldownSeconds] = useState(0)

  useEffect(() => {
    if (cooldownSeconds <= 0) return
    const t = window.setTimeout(() => {
      setCooldownSeconds((s) => Math.max(0, s - 1))
    }, 1000)
    return () => clearTimeout(t)
  }, [cooldownSeconds])

  if (loading) {
    return (
      <div className="flex items-center justify-end gap-2 text-zinc-500">
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
        <span className="sr-only">Loading account</span>
      </div>
    )
  }

  if (user) {
    const label =
      profile?.displayName?.trim() || user.email || 'Signed in'
    return (
      <div className="flex flex-wrap items-center justify-end gap-3">
        <div
          className="flex items-center gap-2 rounded-full border border-zinc-600 bg-zinc-800/80 py-1 pl-1 pr-3"
          title={user.email ?? undefined}
        >
          <span
            className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-600 text-xs font-semibold text-white"
            aria-hidden
          >
            {initials(user.email)}
          </span>
          <span className="max-w-[140px] truncate text-sm text-zinc-200 sm:max-w-[200px]">
            {label}
          </span>
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-600 px-3 py-1.5 text-sm text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800"
          onClick={() => void signOut()}
        >
          <LogOut className="h-4 w-4" aria-hidden />
          Sign out
        </button>
      </div>
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (cooldownSeconds > 0) return
    setFormError(null)
    setSent(false)
    setSending(true)
    const result = await sendMagicLink(email)
    setSending(false)
    if (result.ok) {
      setSent(true)
      setCooldownSeconds(90)
    } else {
      setFormError(
        result.error ??
          'We couldn’t send an email right now, please try again in a few minutes.',
      )
      if (result.rateLimited) {
        setCooldownSeconds((s) => Math.max(s, 180))
      }
    }
  }

  return (
    <div className="flex w-full max-w-md flex-col items-stretch gap-2 sm:max-w-sm sm:items-end">
      {!user && guestId ? (
        <p className="text-right text-xs text-zinc-500">
          You&apos;re in guest mode. Sign in to back up your paths and progress.
        </p>
      ) : null}
      {!isSupabaseConfigured ? (
        <p className="text-right text-xs text-amber-600/90">
          Set <code className="rounded bg-zinc-900 px-1">VITE_SUPABASE_URL</code>{' '}
          and{' '}
          <code className="rounded bg-zinc-900 px-1">VITE_SUPABASE_ANON_KEY</code>{' '}
          in <code className="rounded bg-zinc-900 px-1">.env</code> (repo root).
        </p>
      ) : null}
      {sent ? (
        <p className="rounded-lg border border-emerald-800/60 bg-emerald-950/40 px-3 py-2 text-right text-sm text-emerald-200">
          Check your email for a sign-in link. You can close this tab and open the
          link on any device.
        </p>
      ) : null}
      <form
        className="flex w-full flex-col gap-2 sm:max-w-xs"
        onSubmit={(e) => void handleSubmit(e)}
      >
        <label className="sr-only" htmlFor="auth-email">
          Email address
        </label>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-zinc-600 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
          <button
            type="submit"
            disabled={
              sending ||
              !isSupabaseConfigured ||
              cooldownSeconds > 0
            }
            title={
              cooldownSeconds > 0
                ? `Wait ${cooldownSeconds}s before requesting another email`
                : undefined
            }
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-900 hover:bg-white disabled:opacity-50"
          >
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Mail className="h-4 w-4" aria-hidden />
            )}
            {sending
              ? 'Sending…'
              : cooldownSeconds > 0
                ? `Wait ${cooldownSeconds}s`
                : 'Email me a link'}
          </button>
        </div>
        {formError ? (
          <p className="text-right text-xs text-red-400" role="alert">
            {formError}
          </p>
        ) : null}
        <p className="text-right text-xs text-zinc-500">
          No password — we&apos;ll email you a one-time sign-in link.
        </p>
      </form>
    </div>
  )
}

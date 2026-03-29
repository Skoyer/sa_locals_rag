
# Learning Paths & Auth Spec

This document specifies how to add **learning paths**, **per‑user progress**, and **OAuth‑based profiles** to the Topic Browser React + Vite app using **Supabase Auth** and Postgres.

Supabase is chosen for its generous free tier (50k MAU, Postgres, Auth, storage) and standard OAuth/OIDC flows. [uibakery](https://uibakery.io/blog/supabase-pricing)

***

## 1. Features and UX

### 1.1 Core concepts

- **Profile**  
  - A user account authenticated via Supabase (email and/or OAuth providers).  
  - Stores display name and timestamps.

- **Learning Path**  
  - An ordered list of videos tailored to an interest or goal.  
  - Two types:
    - *Featured paths*: curated, visible to everyone.
    - *User paths*: created by a signed‑in user, private to them.

- **Video Progress**  
  - Whether a user has watched a given video (and when).  
  - Used to show completion status in grids and in each learning path.

### 1.2 High‑level UX

- Add **Sign in / Sign out** to the Topic Browser header.  
- When signed in:
  - Show “Your paths” and progress.  
  - Allow creating/editing paths and tracking watched videos.
- When signed out:
  - All browsing works as now, but saving paths and tracking progress are disabled (show a call‑to‑action to sign in).

#### New UI elements

1. **Header**
   - Right‑side:
     - If logged out: “Sign in” button (opens Supabase Auth flow).
     - If logged in: avatar/initials + menu with “Sign out”.

2. **Tabs above Videos**
   - `Videos | Learning Paths`
   - Default: `Videos` (current Topic Browser view extended with watch markers).

3. **Learning Paths tab**
   - Sections:
     - **Featured paths** (read‑only).  
     - **Your paths** (CRUD for authenticated user).
   - CTA:
     - “Create path from current filters” (uses filtered videos as ordered steps).

4. **Video cards (both tabs)**
   - Show:
     - “✓ Watched” badge (or subtle progress icon) when completed.  
     - “Mark as watched” / “Mark unwatched” toggle for signed‑in users.

5. **Path detail view**
   - Title, description, basic stats (“3 of 12 videos completed”).  
   - Ordered list of steps with:
     - Video title, difficulty, topics.  
     - Completion checkmark and “Watch now” button.

***

## 2. Supabase Setup

> Cursor: follow these steps using the Supabase Dashboard and SQL editor.

1. **Create Supabase project**
   - Use the free plan.  
   - Note the **Project URL** and **anon key** for front‑end config.

2. **Enable Auth providers**
   - In *Authentication → Providers*, enable **Email** (magic link is the default for the Topic Browser app — no Google/GitHub required).
   - Under **Email**, confirm **Confirm email** / **Secure email change** as you prefer; magic links work with **“Enable email confirmations”** off for local testing, or on for production.
   - **Authentication → URL Configuration**, set **Site URL** to your app (e.g. `http://localhost:5173` for local dev) and add the same under **Redirect URLs** so magic-link redirects back to the app.
   - Social providers (Google, GitHub) are optional and **not used** by the current Topic Browser UI.

3. **Create database tables**

Run the following SQL in the Supabase SQL editor:

```sql
-- Profiles are 1:1 with auth.users
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz default now()
);

-- Featured learning paths – curated, visible to everyone
create table public.featured_learning_paths (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  tags text[] default '{}',
  video_ids integer[] not null,
  created_at timestamptz default now()
);

-- User-defined learning paths – private to each user
create table public.user_learning_paths (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  description text,
  tags text[] default '{}',
  video_ids integer[] not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index on public.user_learning_paths (user_id);

-- Per-video progress for each user
create table public.video_progress (
  user_id uuid not null references public.profiles(id) on delete cascade,
  video_id integer not null,
  completed_at timestamptz not null default now(),
  primary key (user_id, video_id)
);
```

4. **Row‑level security (RLS)**

Enable RLS on custom tables and add basic policies:

```sql
alter table public.profiles enable row level security;
alter table public.user_learning_paths enable row level security;
alter table public.video_progress enable row level security;
alter table public.featured_learning_paths enable row level security;

-- Profiles: users can see/update only their own
create policy "Profiles are viewable by owner" on public.profiles
  for select using (auth.uid() = id);

create policy "Profiles are insertable by owner" on public.profiles
  for insert with check (auth.uid() = id);

create policy "Profiles are updatable by owner" on public.profiles
  for update using (auth.uid() = id);

-- Featured paths: readable by everyone, writable only by service role (no client policy for writes)
create policy "Featured paths are readable by everyone" on public.featured_learning_paths
  for select using (true);

-- User paths: owner-only access
-- (PostgreSQL allows only one command per policy: FOR SELECT | INSERT | UPDATE | DELETE | ALL — not "insert, update, delete".)
create policy "User paths are viewable by owner" on public.user_learning_paths
  for select using (auth.uid() = user_id);

create policy "User paths are insertable by owner" on public.user_learning_paths
  for insert
  with check (auth.uid() = user_id);

create policy "User paths are updatable by owner" on public.user_learning_paths
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "User paths are deletable by owner" on public.user_learning_paths
  for delete
  using (auth.uid() = user_id);

-- Video progress: owner-only access
create policy "Video progress is viewable by owner" on public.video_progress
  for select using (auth.uid() = user_id);

create policy "Video progress is insertable by owner" on public.video_progress
  for insert
  with check (auth.uid() = user_id);

create policy "Video progress is updatable by owner" on public.video_progress
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Video progress is deletable by owner" on public.video_progress
  for delete
  using (auth.uid() = user_id);
```

***

## 3. Front‑end Types and Client Setup

### 3.1 Install dependencies

> Cursor: inside `topic-browser/` run:

```bash
npm install @supabase/supabase-js
```

### 3.2 Supabase client

Create `src/lib/supabaseClient.ts`:

```ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

Add `.env.local` (not committed) with keys:

```env
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
```

### 3.3 TypeScript types

Extend `src/types.ts`:

```ts
export interface LearningPathBase {
  id: string;
  title: string;
  description?: string | null;
  tags: string[];
  videoIds: number[];
  createdAt: string;
}

export interface FeaturedLearningPath extends LearningPathBase {
  kind: 'featured';
}

export interface UserLearningPath extends LearningPathBase {
  kind: 'user';
  updatedAt: string;
}

export interface UserProfile {
  id: string;
  displayName?: string | null;
  createdAt: string;
}

export interface VideoProgress {
  userId: string;
  videoId: number;
  completedAt: string;
}
```

***

## 4. Auth and Profile Store

> Cursor: use Zustand or existing global store pattern.  
> **Implemented app:** sign-in is **email magic link** via `sendMagicLink` (not OAuth). See `src/store/useAuthStore.ts` and `src/components/layout/AuthHeader.tsx`.

Create `src/store/useAuthStore.ts` (outline; OAuth snippet below is replaced by magic link in the real project):

```ts
import { create } from 'zustand';
import type { UserProfile, UserLearningPath, VideoProgress } from '../types';
import { supabase } from '../lib/supabaseClient';

interface AuthState {
  user: { id: string; email?: string | null } | null;
  profile: UserProfile | null;
  userPaths: UserLearningPath[];
  progress: VideoProgress[];
  loading: boolean;

  initFromSession: () => Promise<void>;
  sendMagicLink: (email: string) => Promise<{ ok: boolean; error?: string }>;
  signOut: () => Promise<void>;
  toggleVideoWatched: (videoId: number) => Promise<void>;
  saveUserPathFromVideoIds: (
    title: string,
    description: string | undefined,
    videoIds: number[]
  ) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  profile: null,
  userPaths: [],
  progress: [],
  loading: true,

  initFromSession: async () => {
    set({ loading: true });
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.user) {
      set({ user: null, profile: null, userPaths: [], progress: [], loading: false });
      return;
    }

    const user = { id: session.user.id, email: session.user.email };
    const [{ data: profiles }, { data: paths }, { data: progress }] = await Promise.all([
      supabase.from('profiles').select('*').eq('id', user.id).single(),
      supabase.from('user_learning_paths').select('*').eq('user_id', user.id).order('created_at', { ascending: true }),
      supabase.from('video_progress').select('*').eq('user_id', user.id),
    ]);

    // Upsert profile if missing
    let profile = profiles as any;
    if (!profile) {
      const { data: inserted } = await supabase
        .from('profiles')
        .insert({ id: user.id, display_name: session.user.email })
        .select('*')
        .single();
      profile = inserted;
    }

    set({
      user,
      profile: {
        id: profile.id,
        displayName: profile.display_name,
        createdAt: profile.created_at,
      },
      userPaths: (paths ?? []).map((p: any) => ({
        id: p.id,
        kind: 'user',
        title: p.title,
        description: p.description,
        tags: p.tags ?? [],
        videoIds: p.video_ids ?? [],
        createdAt: p.created_at,
        updatedAt: p.updated_at,
      })),
      progress: (progress ?? []).map((r: any) => ({
        userId: r.user_id,
        videoId: r.video_id,
        completedAt: r.completed_at,
      })),
      loading: false,
    });
  },

  sendMagicLink: async email => {
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: window.location.origin + window.location.pathname,
      },
    });
    if (error) return { ok: false, error: error.message };
    return { ok: true };
  },

  signOut: async () => {
    await supabase.auth.signOut();
    set({ user: null, profile: null, userPaths: [], progress: [] });
  },

  toggleVideoWatched: async videoId => {
    const { user, progress } = get();
    if (!user) return;

    const existing = progress.find(p => p.videoId === videoId);
    if (existing) {
      await supabase
        .from('video_progress')
        .delete()
        .eq('user_id', user.id)
        .eq('video_id', videoId);
      set({ progress: progress.filter(p => p.videoId !== videoId) });
    } else {
      const { data, error } = await supabase
        .from('video_progress')
        .insert({ user_id: user.id, video_id: videoId })
        .select('*')
        .single();

      if (!error && data) {
        set({
          progress: [
            ...progress,
            { userId: data.user_id, videoId: data.video_id, completedAt: data.completed_at },
          ],
        });
      }
    }
  },

  saveUserPathFromVideoIds: async (title, description, videoIds) => {
    const { user, userPaths } = get();
    if (!user || videoIds.length === 0) return;

    const { data, error } = await supabase
      .from('user_learning_paths')
      .insert({
        user_id: user.id,
        title,
        description,
        video_ids: videoIds,
      })
      .select('*')
      .single();

    if (!error && data) {
      set({
        userPaths: [
          ...userPaths,
          {
            id: data.id,
            kind: 'user',
            title: data.title,
            description: data.description,
            tags: data.tags ?? [],
            videoIds: data.video_ids ?? [],
            createdAt: data.created_at,
            updatedAt: data.updated_at,
          },
        ],
      });
    }
  },
}));
```

In `src/main.tsx` or `App.tsx`, call `useAuthStore.getState().initFromSession()` on startup.

***

## 5. UI Integration Instructions

### 5.1 Header auth controls

- Modify `AppLayout` header to use `useAuthStore`:

  - If `loading`: show nothing or a spinner.  
  - If `user` is null:
    - Show email field + “Email me a link”; call `sendMagicLink(email)` (magic link via Supabase Email provider).
  - If `user` exists:
    - Show user initial or email and “Sign out” in a small menu.

### 5.2 Tabs: Videos vs Learning Paths

- Add tab state in the layout (local React state): `activeTab: 'videos' | 'paths'`.  
- Render:
  - `Videos` tab: current Topic Browser (`ActiveFiltersBar`, `VideoGrid`, etc.).  
  - `LearningPathsTab` for the new experience.

Create `src/components/paths/LearningPathsTab.tsx`:

- Reads:
  - `user`, `userPaths` from `useAuthStore`.  
  - `allVideos` from existing video store.  
- Shows:
  - Section “Featured paths” (placeholder for now; read from `featured_learning_paths` later).  
  - Section “Your paths”:
    - If not signed in: message + “Sign in to create your own learning paths.”  
    - If signed in and no paths: empty state + “Create path from current filters” button.

- “Create path from current filters”:
  - Reads current filtered video ids from existing `useTopicBrowserStore` selector.  
  - Prompts for a title and description (simple `prompt` or small modal).  
  - Calls `saveUserPathFromVideoIds(title, description, videoIds)`.

- Each path is displayed as a card with:
  - Title, description, tag chips, and “X of Y completed” using `progress`.

### 5.3 Path detail view (optional v1)

- For v1, clicking a path can:
  - Either filter the video grid to just that path’s videos, and show a pill: `Path: {title}`.  
  - Or navigate to a simple detail view component.

Implementation hint:

- Add `activePathId` and `activePathVideoIds` to `useTopicBrowserStore` or local state in `LearningPathsTab`.  
- When a path is activated:
  - Override the filtered videos list to those `videoIds` (still respecting search and topics if desired, or ignore filters).

### 5.4 Video watched indicator

- In `VideoCard.tsx`:
  - Use `const { user, progress, toggleVideoWatched } = useAuthStore();`
  - Determine `isWatched = !!progress.find(p => p.videoId === video.id);`
  - UI changes:
    - If `isWatched`: show a small “✓ Watched” badge in the card header.  
    - If `user` exists: show a button/link “Mark watched / Mark unwatched” that calls `toggleVideoWatched(video.id)`.  
    - If no user: show subtle text “Sign in to track progress”.

This directly ties Supabase‑backed progress to the existing grid, without changing how videos are loaded.

***

## 6. Future Enhancements (for later)

- **Featured paths**:  
  - Add an admin‑only interface (or manual SQL) to insert curated paths into `featured_learning_paths`.  
  - Front‑end reads them with a simple `supabase.from('featured_learning_paths').select('*')`.

- **Encouraging messages**:
  - Add fields like `lastWatchedAt` and streak calculations client‑side, or via scheduled jobs.  
  - Use a small banner above the grid: “Nice work—3 videos watched this week!”

- **Email notifications**:
  - Use Supabase Edge Functions or an external scheduler to send occasional emails based on `video_progress` activity.

***


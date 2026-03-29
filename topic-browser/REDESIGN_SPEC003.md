## Context

On the **Videos** screen after selecting an interest (e.g., Persuasion) and choosing to **review/customize** the starter path, the UI currently shows:

- A purple path header (“Path: Persuasion — 22‑lesson starter path”).
- A brown banner (“You’re reviewing this lesson set — save it as your own path when you’re ready.”).
- A disabled “Save as my custom path” button.
- A filtered video grid for that interest.

Problems:

1. Users cannot remove an individual video from this starter set.
2. It is not obvious (or even possible) how to add videos to this starter set.
3. “Save as my custom path” remains disabled, so the flow never completes.
4. After logging out, logging back in via email magic link is unreliable (no new email delivered).
5. We want anonymous “guest” usage, with optional upgrade to a logged‑in profile later.

Implement the changes below.

***

## 1. Make starter paths truly customizable

### 1.1 Per‑video remove control

- In `VideoCard` (only when a path is active and we are in “review/customize” mode):
  - Add a small “Remove from path” affordance:
    - Either an “X” chip/button near the bottom or an icon button in the card header.
  - Clicking it removes that videoId from the **currently reviewed path set** in state without affecting any saved featured path definition.

Implementation details:

- Introduce a `reviewPathDraft` concept in the store (or reuse existing path draft state):
  - When user clicks “Review and customize these N videos” from the interest modal:
    - Create `reviewPathDraft.videoIds` as a copy of the starter path’s videoIds.
    - `filteredVideos` in the Videos tab should derive from `reviewPathDraft.videoIds` instead of the original set while in review mode.
  - `Remove from path` updates `reviewPathDraft.videoIds` and triggers a re-filter.

- Visually indicate removal:
  - Once removed, the card should disappear from the current grid.
  - If all videos are removed, show an empty state: “This path is empty. Add videos from Topics/Clusters or clear and start again.”

### 1.2 Add videos to the draft path

- While in review/customize mode:
  - Any video displayed in the grid that is **not** already in `reviewPathDraft.videoIds` should show an “Add to path” control.
  - Clicking “Add to path” should append that videoId to the end of `reviewPathDraft.videoIds`.

Behavior rules:

- Keep `Topics`, `Clusters`, and search working as discovery filters **on top of** review mode:
  - User can change topics/clusters/search to surface more videos.
  - When they click “Add to path” on a new card, it adds to the draft and that video is considered part of the path even if hidden by filters later.

- Provide a small summary line above the grid while in review mode:
  - “You have X videos in your custom path draft. Use ‘Remove from path’ or ‘Add to path’ on any video card to customize.”

### 1.3 Enable “Save as my custom path”

- The purple header with “Save as my custom path” should behave as follows:

  - Enabled when:
    - User is signed in **AND**
    - `reviewPathDraft.videoIds.length >= 1`.

  - Disabled when:
    - User is signed out (show a tooltip or small text: “Sign in to save your custom path.”).
    - OR `reviewPathDraft.videoIds` is empty.

- On click:
  - Prompt for a path title (default: “{Interest} — My custom path”).
  - Call the existing Supabase path save function (user_learning_paths insert) with `reviewPathDraft.videoIds` and the chosen title.
  - After successful save:
    - Show a success toast: “Path saved. You can find it under ‘Your paths’.”
    - Option 1 (simplest): Clear review mode and navigate back to Learning Paths tab.
    - Option 2: Keep the path active in Videos tab but swap banner text to “You’re viewing your saved path: {title}.”

- Also add a third button or link in the brown banner:
  - “Clear review” — resets `reviewPathDraft` and returns to normal filtered grid state.

***

## 2. Fix login issues and add anonymous usage

### 2.1 Make the magic‑link login reliable

- Investigate the current Supabase Auth integration:

  - Ensure we call **either** `signInWithOtp` (email) or `signInWithOAuth`, not both together.
  - Confirm `redirectTo` is set correctly to the current origin and that we are handling `supabase.auth.onAuthStateChange` or `getSession()` on load.

- Bug to fix:
  - After signing out, requesting a new email link doesn’t send an email.
  - Possible issues:
    - Rate limiting or code path silently failing.
    - Unhandled error from Supabase.

- Add explicit error and success feedback near the email field:
  - On success: “Check your email for a sign‑in link.”
  - On error: surface the message from Supabase (e.g., “We couldn’t send an email right now, please try again in a few minutes.”).

- Log any Supabase auth errors to the console and show a user-facing message.

### 2.2 Add anonymous “guest” usage

Goal: allow a user to use the app and build a path *without* signing in, with the option to later attach their guest data to a real account.

Implementation:

1. Add a **guest mode** to the auth store:
   - Fields:
     - `isGuest: boolean`
     - `guestId: string | null` (e.g., a UUID stored in localStorage)
   - On initial page load:
     - If there is no Supabase user and no existing guestId:
       - Generate a new guestId, save it to localStorage, and set `isGuest = true`.
     - If guestId exists: keep using it.

2. Path and progress behavior in guest mode:
   - Allow creating/saving “local” paths and video progress using the same store structure, but persisted **only to localStorage**, not Supabase.
   - In the UI:
     - Show a subtle label: “You’re in guest mode. Sign in to back up your paths and progress.”

3. When the user signs in for the first time:
   - After successful Supabase auth and profile creation, **merge guest data**:
     - For each guest path, insert into `user_learning_paths` for this user.
     - For each guest video progress record, insert into `video_progress` (if not already there).
   - After merge, clear guest paths/progress from localStorage and set `isGuest = false`.

4. CTAs:

   - Keep a simple “Email me a link” or “Sign in” control in the header.
   - On the Learning Paths tab, add copy like:
     - “Your paths are stored in this browser only. Sign in to access them from any device.”

***

## 3. UX tweaks for clarity

- In the brown review banner (under the purple path header), use clearer copy:

  - “You’re reviewing this starter set. Remove any lessons you don’t want, add new ones from the sidebar or search, then save it as your own path.”

- On each `VideoCard` in review mode:
  - Replace “Sign in to track progress” with:
    - If signed in: show progress + “Remove from path / Add to path”.
    - If guest: show progress + text “In guest mode — sign in later to keep this path.”

***

## 4. Definition of Done

- A user can:
  - Click an interest tile, choose to review/customize the starter path.
  - Remove individual videos from that draft.
  - Add additional videos from topics/clusters/search.
  - Save the customized set as their own path when signed in.
- “Save as my custom path” is enabled whenever there is at least one video in the draft and the user is signed in; otherwise it is disabled with clear explanation.
- Logging out and then requesting a new email login works reliably, with visible error/success messages for auth.
- Anonymous/guest usage works:
  - Paths and progress persist in localStorage.
  - On first sign-in, guest data merges into the real account.

***

Use TypeScript throughout and keep naming consistent with the existing stores and components.
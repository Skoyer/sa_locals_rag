## 1) Default learning path for each “What do you want to get better at?” tile

Goal: every interest tile (Thinking, Persuasion, Energy, Creativity, Career, Health) should *always* have a default learning path, and “Browse all” is the advanced/customize option.

Requirements:

1. For each interest tile:
   - When the user clicks a tile, **assume a default learning path exists** for that interest.
   - In the interest modal:
     - Replace the “No matching featured path…” message with a recommended path block when one exists.
     - Show:
       - Title: “{Interest} — {N}-lesson starter path”
       - Short description: “We’ve picked a sequence of lessons to build your {interest} skills step by step.”
     - Buttons:
       - Primary (prominent): **“Start this {Interest} path”**
       - Secondary: **“Review and customize these {N} videos”**

2. Behavior for the primary button:
   - Create/activate a learning path using the predefined videoIds for that interest (from featured paths or a mapping inside the app).
   - Switch to the Videos tab.
   - Filter to that path’s videos **in order** and show the path progress header (Path title + X of Y complete) as already defined in the redesign spec.

3. Behavior for the secondary button:
   - Switch to the Videos tab.
   - Filter the grid to the same set of videos (path videoIds), but:
     - Do NOT immediately save the path.
     - Allow the user to add/remove videos (existing “Add to path” / “Mark as watched” UX).
   - Provide a “Save as my custom path” button near the top that persists a user path with the current filtered list.

4. If a tile has no curated path defined yet:
   - Fallback to current behavior, but:
     - Still show a primary button: “Create a starter path from these {N} videos”.
     - Clicking it should save a new user path using those filtered videos, name it “{Interest} Starter”, and then behave as above.

## 2) “Remaining unwatched videos” path (finish the library)

Goal: allow a signed-in user to watch the entire remaining library in a recommended order.

Requirements:

1. In the Learning Paths tab:
   - Under “Your paths”, add a persistent card that reflects user progress:
     - If user has any unwatched videos:
       - Card title: **“Everything you haven’t watched yet”**
       - Subtitle: “Continue through all remaining lessons in a smart order.”
       - CTA button: **“Start ‘Watch Everything’ path”**
     - If user has watched all videos:
       - Card title: “You’ve watched every lesson!”
       - Subtitle: “New lessons will appear here when available.”
       - No CTA needed.

2. When the user clicks “Start ‘Watch Everything’ path”:
   - Compute remaining videos as: `allVideos - watchedVideos` using the existing progress store.
   - Build an ordered list of videoIds using a simple heuristic:
     - Group by main topic bucket (e.g., persuasion, thinking, energy, creativity, career, health).
     - Within each group, sort by difficulty (beginner → intermediate → advanced) if that field exists; otherwise by transcript_id or title.
     - Interleave groups to avoid long runs of a single topic (simple round-robin over groups is fine).
   - Save/activate a learning path with:
     - Title: “Watch Everything You Haven’t Seen”
     - Description: “Automatically updated list of all remaining lessons.”
     - videoIds: ordered list computed above.

3. Path behavior:
   - Use the same path progress header and per-video watched indicators as other paths.
   - As the user marks videos watched:
     - They should disappear from this path on next recompute or page reload.
     - Minimum implementation: recompute the path whenever the user reopens the Learning Paths tab or clicks the card again, so it always reflects current unwatched videos.

4. Edge cases:
   - If there are 0 remaining videos when the user clicks the card, show a toast/message: “You’ve already watched every lesson. Great work!” and do not create/activate a path.
   - If not signed in:
     - Show the card but disable the CTA.
     - Text: “Sign in to track what you’ve watched and finish the whole library.” with a Sign in button that triggers existing auth.

Implementation notes:

- Reuse the existing learning-path and progress stores; do not introduce a new store.
- Prefer to keep the “Watch Everything” path **derived** (recomputed) rather than permanently stored, so it always matches the latest watched state.
- Ensure TypeScript compiles cleanly and the new UI is consistent with the existing styling (buttons, modals, path cards).
# Scott Adams Locals Micro Lessons Library – UI Spec

This spec defines UI and behavior changes for:

- `web/index.html` – static HTML/CSS/vanilla JS version.
- `web2/` – new React + Vite app that implements the same features, unless a feature is explicitly marked as `web2-only`.

When in doubt, keep behavior and layout consistent between both versions.

---

## 1. Project setup

### 1.1 Existing `web` app

- Keep `web/index.html` as a static, no-build HTML page.
- You may add:
  - A small site-specific CSS file (e.g., `web/styles.css`).
  - A small JS file (e.g., `web/app.js`) loaded at the bottom of `index.html`.

### 1.2 New `web2` React + Vite app

- Create a new React app:

  ```bash
  npm create vite@latest web2 -- --template react
  ```

- Implement the same UI and behavior described in this spec using React components.
- Use function components and hooks (no class components).

---

## 2. Global layout and header

### 2.1 Page title text

- Replace the current main page title text:

  - From: `Scott Adams Persuasion Library`
  - To: `Scott Adams Locals Micro Lessons Library`

- Do this in both:
  - The primary `<h1>` in `web/index.html`.
  - The React component that renders the page header in `web2`.

### 2.2 Logo placement

- The repository includes a `logo.png` file (provided externally).
- Add the logo in the header, **above** the word cloud and aligned with the title and subtitle:

  - In `web/index.html`, place:

    ```html
    <header id="site-header">
      <img id="site-logo" src="logo.png" alt="Scott Adams Locals Micro Lessons Library logo" />
      <h1>Scott Adams Locals Micro Lessons Library</h1>
      <p id="site-subtitle">
        An unofficial guide for Scott’s beloveds in the Coffee With Scott Adams / Scott Adams School community:
        explore all the Locals‑only Micro Lessons by theme, skim friendly descriptions, and search the full library in your browser.
      </p>
    </header>
    ```

  - In `web2`, create a `Header` component with the same structure.

- Style the logo so that:

  - It sits above or to the left of the title but visually aligned with the title text.
  - It is smaller than the raw image size, e.g.:

    ```css
    #site-logo {
      max-height: 80px;
      display: block;
      margin-bottom: 0.5rem;
    }
    ```

### 2.3 Subtitle text replacement

- Replace any existing helper text like:

  - `Local RAG pipeline export — open this file in a browser (no server).`

- With this exact sentence (single paragraph):

  - `An unofficial guide for Scott’s beloveds in the Coffee With Scott Adams / Scott Adams School community: explore all the Locals‑only Micro Lessons by theme, skim friendly descriptions, and search the full library in your browser.`

### 2.4 Stats line position and content

- There is a stats line currently near the top that reads (or is equivalent to):

  - `Videos: 260 Clusters: 15 Topic tags: 206 Persuasion-focused: 16.9%`

- Change it as follows:

  - Remove the `Persuasion-focused: 16.9%` part.
  - Final text: `Videos: 260 Clusters: 15 Topic tags: 206`
  - Move this line to the **bottom of the page**, just above any footer or the last section.

---

## 3. Sections and visibility

### 3.1 Remove Topic Tree

- Completely remove the **Topic Tree** section from both `web` and `web2`:

  - Delete the Topic Tree heading and its nested lists / expanders.
  - Remove any JS code that manipulates or listens to Topic Tree elements.

### 3.2 Rename “Clusters” section

- Wherever the “Clusters” heading appears, change its label to:

  - `Lesson Themes`

- If there are internal references (e.g., nav links, aria labels), update them to “Lesson Themes” as well.

---

## 4. Titles normalization (clusters and videos)

> Goal: Remove “Micro Lesson(s)” phrasing from all user-facing titles and standardize formatting.

### 4.1 Data fields

- The data for clusters and videos may come from a pipeline (e.g., LM Studio).
- Add or use **derived fields** where possible:

  - `cluster.title_original` – original title string.
  - `cluster.title2` – **normalized cluster title** used in the UI.
  - `video.title_original` – original title string (e.g., from transcripts).
  - `video.display_title` – **normalized video title** used in the UI.
  - `video.short_description` – short text used in tooltips.

- If `title2` or `display_title` are not available at runtime, fall back to computing them in JS using the rules below.

### 4.2 Cluster title normalization

- For cluster titles:

  - Remove any leading phrases:
    - `Micro Lessons on `
    - `Micro Lesson on `
  - Apply standard title case to the remainder.
  - Examples:
    - `Micro Lessons on Imagination and Creativity` → `Imagination and Creativity`
    - `Micro Lesson on Time Management & Systemic Issues` → `Time Management & Systemic Issues`

- Implementation:

  - Preferred: The pipeline populates `title2` following this rule.
  - UI code (both `web` and `web2`) should:
    - Render `title2` when present.
    - Else, apply a small normalization helper:

      ```js
      function normalizeClusterTitle(raw) {
        if (!raw) return '';
        return raw
          .replace(/^Micro Lessons? on\s+/i, '')
          .replace(/\s+/g, ' ')
          .trim()
          .replace(
            /\w\S*/g,
            (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase()
          );
      }
      ```

### 4.3 Video title normalization

- For each video title:

  - Original pattern example:
    - `#232 — A Micro Lesson on being careful what you measure`
  - Transform according to these rules, in order:

    1. Extract the episode number if present:

       - Match leading `#<number>` optionally followed by punctuation or a dash.
       - Store as `episodeNumber` (e.g., `232`).

    2. Remove the leading `#<number>` and any separators (`—`, `-`, `:`) from the title string.

    3. Remove the phrases:

       - `A Micro Lesson on `
       - `A Micro Lesson about `
       - Case-insensitive.

    4. Trim whitespace and apply title case to the remaining phrase.

    5. Re-append the episode number **at the end** in parentheses.

- Example:

  - Input: `#232 — A Micro Lesson on being careful what you measure`
  - Output `display_title`: `Being Careful What You Measure (#232)`

- Implementation:

  ```js
  function normalizeVideoTitle(raw) {
    if (!raw) return '';

    let episodeMatch = raw.match(/^#(\d+)\s*[—:-]?\s*/);
    let episodeNumber = episodeMatch ? episodeMatch : null;[16]
    let title = raw.replace(/^#\d+\s*[—:-]?\s*/i, '');

    title = title.replace(/^A Micro Lesson (on|about)\s+/i, '');
    title = title.trim();

    // Title case
    title = title.replace(
      /\w\S*/g,
      (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase()
    );

    if (episodeNumber) {
      return `${title} (#${episodeNumber})`;
    }
    return title;
  }
  ```

- UI usage:

  - Prefer `video.display_title` from the pipeline when available.
  - Otherwise, call `normalizeVideoTitle(video.title_original)` in JS/React.

- **Apply this normalized format everywhere video titles are rendered** (cluster cards, search results, main Videos section, etc.).

---

## 5. Layout and search behavior

### 5.1 High-level layout

- Below the header and the main word cloud:

  - Add a **two-column layout** (on desktop) that contains:
    - **Left column (1/3 width):**
      - Search input at the top.
      - List of matching videos (search results) below.
    - **Right column (2/3 width):**
      - “Lesson Themes” section (formerly Clusters) showing cluster cards.

- Desktop layout:

  ```css
  .content-layout {
    display: grid;
    grid-template-columns: 1fr 2fr; /* left 1/3, right 2/3 */
    gap: 2rem;
    margin-top: 2rem;
  }

  @media (max-width: 900px) {
    .content-layout {
      grid-template-columns: 1fr;
    }
  }
  ```

- Structure for `web/index.html` (React version should mirror this in JSX):

  ```html
  <main>
    <section id="wordcloud-section">
      <!-- existing word cloud element here -->
    </section>

    <section id="library-section" class="content-layout">
      <div id="search-column">
        <!-- search input + filtered video list -->
      </div>
      <div id="themes-column">
        <!-- Lesson Themes (clusters) cards -->
      </div>
    </section>
  </main>
  ```

### 5.2 Default visibility

- On initial page load:

  - **Visible**:
    - Header (logo, title, subtitle).
    - Main word cloud.
  - **Hidden**:
    - Search input and results list.
    - Lesson Themes section.
    - Stats line at the bottom is still present (as per section 2.4).

- Show library content under either of these triggers:

  1. When the user focuses the search input (or starts typing).
  2. When the user clicks a “Browse lessons” button (if added).

- Implementation suggestion:

  - Add a CSS class like `.hidden { display: none; }`.
  - Remove the `hidden` class from `#library-section` when:

    - The search input receives `input` or `focus` events.
    - Or when `Browse lessons` is clicked.

### 5.3 Search input and behavior

- Add a prominent search input in the **left column**, labeled clearly:

  ```html
  <label for="lesson-search">Search lessons</label>
  <input
    type="search"
    id="lesson-search"
    placeholder="Search by title or description..."
  />
  <div id="search-results"></div>
  ```

- Behavior (both `web` and `web2`):

  - As the user types, update the search results **in real time** (no form submit needed).
  - Filtering rules:

    - Case-insensitive.
    - Match on:
      - Normalized video title (`display_title` or normalized from original).
      - The short description (`video.short_description`) if available.

  - When search text is empty:

    - Option A (simple): show all videos in the search results list.
    - Option B (if performance is a concern): show none and display a helper message like “Start typing to search the library”.

- Result rendering:

  - Each result entry should show:

    - The **normalized video title** (per section 4.3).
    - Optionally, a small excerpt of the short description.

  - Each result entry’s title is clickable and links directly to the Locals video.

---

## 6. Lesson Themes (clusters) UI

### 6.1 Renamed heading

- Top heading for the clusters section:

  ```html
  <h2>Lesson Themes</h2>
  ```

- Use the normalized cluster titles in cards, as defined in section 4.2.

### 6.2 Cluster cards

- For each cluster:

  - Display:
    - The normalized cluster title.
    - The cluster word cloud image (if present).
    - A list of video links belonging to that cluster (see section 7 for video formatting).
  - Ensure all cluster titles are rendered in title case.

- Scrolling behavior:

  - If a cluster card contains many videos, it can have its own internal scroll (as in the original UI), but preserve existing behavior unless a change is required to match this spec.

---

## 7. Video tiles and tooltips

### 7.1 Section name

- Rename the main “Videos” heading (if present at the top of the video list) to:

  - `Lesson Library`

- This heading can appear above the search results list or near the word cloud, but should be clearly associated with the list of individual lessons.

### 7.2 Title formatting

- Every video title displayed anywhere in the UI must follow the normalization rules from section 4.3.
- Example final display:

  ```text
  Being Careful What You Measure (#232)
  ```

### 7.3 Links and “Open on Locals”

- Remove any separate “Open on Locals” links or buttons from video tiles.
- Make the video title itself a clickable link to the Locals URL:

  ```html
  <a
    href="https://scottadams.locals.com/post/..."
    target="_blank"
    rel="noopener noreferrer"
    title="SHORT DESCRIPTION HERE"
  >
    Being Careful What You Measure (#232)
  </a>
  ```

- Apply this both:

  - In cluster cards (list of videos within each theme).
  - In the search results / Lesson Library list.

### 7.4 Tooltips

- Use `video.short_description` (from the pipeline) as the tooltip text for each video:

  - Implement using the HTML `title` attribute on the clickable title.

- If no short description exists, omit the tooltip or fall back to a safe default like:

  - `Micro lesson video`

---

## 8. Accessibility and responsiveness

- Ensure:

  - Heading hierarchy remains logical (`h1` for main title, `h2` for major sections, `h3` inside cards if needed).
  - All interactive elements are keyboard-accessible.
  - Labels are associated with their inputs (`for` / `id` pairing).

- Responsive behavior:

  - On narrow screens (`max-width: 900px`), stack the columns vertically:

    - Search + results on top.
    - Lesson Themes (clusters) below.

---

## 9. Implementation priorities

When implementing with Cursor:

1. Update header (title, logo, subtitle) and stats line placement.
2. Remove Topic Tree and rename Clusters → Lesson Themes.
3. Implement title normalization helpers (JS + React) and wire them to clusters and videos.
4. Implement two-column layout with responsive CSS.
5. Add real-time search on the left with normalized titles and links.
6. Update video tiles:
   - Remove “Open on Locals”.
   - Make titles clickable to Locals.
   - Add tooltips from `short_description`.
7. Apply default visibility (hide library until search or browse action).

This spec should be treated as the source of truth for all UI and behavior changes related to the Scott Adams Locals Micro Lessons Library page.
# Web Interface

SA Locals RAG includes a static web UI that renders the analyzed video library as a browsable HTML page, as well as a nascent interactive RAG chat interface.

---

## Current Static Site

The `web/` directory contains the static site generator and output. Running the pipeline produces an HTML page with:

- **Playlist navigation** — sidebar or tab-based navigation by cluster/topic bucket
- **Video cards** — title, summary, primary topics, difficulty badge, and a link back to the original Locals.com post
- **Search** — client-side fuzzy search over titles and summaries
- **Word clouds** — per-cluster word cloud images from `wordclouds/`

### Generating the Site

```bash
# The site is regenerated automatically at the end of run_full_pipeline.py
# or you can run the web module directly:
python -m web.generate
```

Output is written to `web/index.html` (and supporting assets).

---

## Planned Web App (Future)

The roadmap includes a full-featured web application to replace the static site. See [roadmap.md](roadmap.md) for the full feature list. Key planned features include:

### User Authentication
- User registration and login (email + password, OAuth options)
- Session management with secure cookies
- Role-based access: admin, contributor, viewer

### Session Tracking
- Users can mark videos as watched, in-progress, or want-to-watch
- Personal viewing history with timestamps
- Progress bars and completion percentages per playlist/cluster

### Social Features
- Per-video comment threads (users can discuss content)
- Link sharing — attach external links (articles, YouTube videos, related resources) to any video
- Topic tagging by users
- Upvoting/downvoting comments

### Enhanced Playlist Interface
- Richer playlist view with auto-play and queue management
- Filter by difficulty, topic, tone, cluster, or date range
- Recommended "next video" based on content similarity
- Custom user-created playlists

### Admin Dashboard
- Pipeline status monitoring
- Trigger pipeline stages from the web UI
- View download failures and retry them
- Database statistics and visualizations

---

## Planned Tech Stack (Web App)

| Layer | Candidate Technology |
|---|---|
| Backend | FastAPI or Flask |
| Auth | FastAPI-Users / Flask-Login |
| Database | SQLite (existing) + user/session tables |
| Frontend | HTMX + Tailwind CSS (or React) |
| Deployment | Docker + nginx or Railway/Render |

---

## Current `sa_rag_chat.py` Interface

The current interactive interface is a terminal-based RAG chatbot:

```bash
python sa_rag_chat.py
```

It uses FTS5 to retrieve the most relevant transcripts for a user query, then sends them as context to the OpenAI API. The planned web app will expose this as a web-based chat widget.

---

## Improving the Static Page

Short-term improvements planned for the static page (before the full web app):

- **Transcript viewer** — expand a video card to read the full transcript inline
- **Timeline view** — sort videos by `posted_at` date on a visual timeline
- **Concept graph** — D3.js graph linking videos by shared `key_concepts`
- **Export buttons** — download a playlist as CSV, JSON, or M3U

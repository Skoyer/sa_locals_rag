# Roadmap

This document tracks planned features and improvements for SA Locals RAG, organized by priority.

---

## Near-Term (Current Sprint)

### Pipeline
- [ ] Configurable stage flags in `run_full_pipeline.py` (e.g., `--skip-download`, `--skip-transcription`)
- [ ] Progress bar for batch transcription and LLM analysis
- [ ] Graceful interrupt handling (save state before exit)
- [ ] Rate limiting / backoff for OpenAI API calls

### Static Web UI
- [ ] Transcript viewer (expand card to read full transcript)
- [ ] Timeline view sorted by `posted_at`
- [ ] Filter bar (difficulty, topic, cluster, persuasion flag)
- [ ] Export playlist to CSV / JSON / M3U
- [ ] D3.js concept graph (nodes = videos, edges = shared key concepts)

---

## Medium-Term

### Web Application (Phase 1 — Auth + Tracking)
- [ ] FastAPI backend replacing static generation
- [ ] User registration and login
- [ ] Session tracking (watched, in-progress, want-to-watch)
- [ ] Personal watch history dashboard

### Web Application (Phase 2 — Social)
- [ ] Per-video comment threads
- [ ] Attach external links/resources to videos
- [ ] User tagging and annotation
- [ ] Comment upvoting/downvoting

### Web Application (Phase 3 — RAG Chat)
- [ ] Web-based RAG chat interface
- [ ] Conversation history persistence
- [ ] Source citations in chat responses (link to video)
- [ ] Multi-user chat with shared context

---

## Long-Term

### Enhanced Analysis
- [ ] Vector embeddings (OpenAI or local) for semantic similarity playlists
- [ ] Cross-reference detection ("This video refers to Episode X")
- [ ] Sentiment trend analysis over time
- [ ] Auto-generated topic learning paths (prerequisite graph)

### Infrastructure
- [ ] Docker Compose setup for one-command deployment
- [ ] Scheduled pipeline runs (cron / Celery)
- [ ] Webhook notifications (Discord/Slack) when new videos are processed
- [ ] Cloud deployment guide (Railway, Render, or self-hosted)

### Content
- [ ] Support for multiple Locals.com creators / playlists
- [ ] YouTube playlist support as an alternate source
- [ ] Podcast RSS feed output

---

## Known Limitations

| Issue | Status | Notes |
|---|---|---|
| Locals.com Cloudflare blocks direct `webapi.locals.com` API access | Known | `LOCALS_ENABLE_API_PROBE` workaround; usually resolved via Playwright |
| HLS token (`vt=`) expiry | Known | Tokens expire; `retry_failed_hls.py` re-fetches fresh URLs |
| Infinite scroll cap at 80 scrolls | Known | Sufficient for ~260 videos; configurable if needed |
| Whisper accuracy on fast speech | Known | Use `medium` or `large` model for better results |

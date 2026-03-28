# Configuration Reference

All configuration is managed through environment variables, loaded from a `.env` file in the project root via `config.py`.

---

## Core Settings

### Locals.com Authentication

| Variable | Default | Description |
|---|---|---|
| `LOCALS_EMAIL` | *(required)* | Email address for Locals.com login |
| `LOCALS_PASSWORD` | *(required)* | Password for Locals.com login |
| `LOCALS_COOKIES_PATH` | `locals_cookies.txt` | Path to the Netscape-format cookie file |
| `LOCALS_PLAYLIST_URL` | *(required)* | Full URL of the playlist to scrape |
| `LOCALS_HEADLESS` | `1` | Set to `0` to show the browser window during scraping |

### OpenAI / LLM

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required for LLM stage)* | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | Model to use for transcript analysis |
| `OPENAI_MAX_TOKENS` | `2000` | Max tokens per LLM analysis call |

### Whisper / Transcription

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `WHISPER_DEVICE` | `cpu` | Compute device: `cpu` or `cuda` |
| `WHISPER_LANGUAGE` | `en` | Language hint for Whisper (ISO 639-1) |

### Database

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `playlist_archive.db` | Path to the SQLite database file |

### Download Behavior

| Variable | Default | Description |
|---|---|---|
| `DOWNLOAD_DIR` | `data/videos` | Directory where video files are saved |
| `TRANSCRIPT_DIR` | `data/transcripts` | Directory where transcript files are saved |
| `MAX_DOWNLOAD_WORKERS` | `2` | Number of parallel download threads |

---

## Debug / Development Settings

| Variable | Default | Description |
|---|---|---|
| `LOCALS_DEBUG_HTML` | *(unset)* | Set to any value to save raw HTML from Playwright to debug files |
| `LOCALS_DEBUG_API` | *(unset)* | Set to any value to log Locals API probe responses |
| `LOCALS_ENABLE_API_PROBE` | `0` | Set to `1` to enable direct `webapi.locals.com` API probing (blocked by Cloudflare in most cases) |

---

## Example `.env` File

```dotenv
# ── Locals.com ──────────────────────────────────────
LOCALS_EMAIL=your@email.com
LOCALS_PASSWORD=yourpassword
LOCALS_PLAYLIST_URL=https://scottadams.locals.com/feed?playlist=12345
LOCALS_COOKIES_PATH=locals_cookies.txt
LOCALS_HEADLESS=1

# ── OpenAI ───────────────────────────────────────────
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o

# ── Whisper ──────────────────────────────────────────
WHISPER_MODEL=small
WHISPER_DEVICE=cpu

# ── Paths ────────────────────────────────────────────
DB_PATH=playlist_archive.db
DOWNLOAD_DIR=data/videos
TRANSCRIPT_DIR=data/transcripts
```

---

## Cookie File Format

The cookie file must be in **Netscape format** (tab-separated). You can export cookies from your browser using a browser extension like "Get cookies.txt LOCALLY". Each line has seven fields:

```
domain \t include_subdomains \t path \t secure \t expiry \t name \t value
```

If `LOCALS_EMAIL` and `LOCALS_PASSWORD` are set, the system will automatically log in via Playwright and regenerate the cookie file if it is missing or empty.

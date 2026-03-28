# Contributing

Thank you for your interest in improving SA Locals RAG!

---

## Development Setup

```bash
git clone https://github.com/Skoyer/sa_locals_rag.git
cd sa_locals_rag
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # fill in your credentials
```

---

## Project Layout

```
sa_locals_rag/
├── config.py               # Central config loader
├── locals_auth.py          # Playwright login
├── locals_fetcher.py       # Playlist scraping & stream URL extraction
├── downloader.py           # Video download orchestration
├── db.py                   # SQLite helpers
├── main.py                 # Download entry point
├── run_full_pipeline.py    # End-to-end pipeline runner
├── run_transcription.py    # Transcription entry point
├── run_once.py             # Single-run download
├── sa_rag_chat.py          # CLI RAG chat
├── transcription/
│   ├── audio.py            # ffmpeg audio extraction
│   ├── whisper_runner.py   # Whisper ASR
│   ├── pipeline.py         # Transcription orchestrator
│   ├── sync.py             # DB sync for existing transcripts
│   ├── cli.py              # CLI entry point
│   └── config.py           # Transcription config
├── pipeline/
│   └── llm_pipeline.py     # LLM analysis pipeline
├── nlp/                    # NLP / clustering
├── rag/                    # RAG retrieval helpers
├── web/                    # Static site generator
├── help_indexer/           # External help doc indexer
├── wordclouds/             # Word cloud image output
├── data/                   # Downloaded videos & transcripts (gitignored)
├── docs/                   # This documentation
└── .env.example            # Example environment file
```

---

## Code Style

- Follow **PEP 8** with 4-space indentation
- Use **type hints** on all public functions
- Keep functions under ~80 lines; extract helpers for complexity
- Use `pathlib.Path` instead of string path concatenation
- Prefer `sqlite3` parameter binding (`?` placeholders) — never f-string SQL

---

## Adding a New Pipeline Stage

1. Create a new module in the appropriate directory (e.g., `pipeline/my_stage.py`)
2. Add a `run_my_stage()` function that accepts standard args (`limit`, `force`, etc.)
3. Call it from `run_full_pipeline.py` in the correct order
4. Document the stage in [pipeline.md](pipeline.md)
5. Add CLI options in [cli-reference.md](cli-reference.md)

---

## Adding a New Database Column

1. Add the column definition to `_VIDEO_RAG_COLUMNS` in `db.py` (or the appropriate list)
2. The migration system will automatically add the column on the next run
3. If the column should be preserved across UPSERTs, add it to the `ON CONFLICT DO UPDATE` block in `insert_video()`
4. Update [database.md](database.md) with the new column description

---

## Pull Request Guidelines

- Open an issue first for major features
- Keep PRs focused — one feature or fix per PR
- Include a brief description of what changed and why
- Test against a real database if possible
- Update documentation in `docs/` to reflect your changes

---

## Useful Dev Commands

```bash
# Check DB state without running pipeline
python check_progress.py

# Test a single post download with debug output
LOCALS_DEBUG_HTML=1 LOCALS_HEADLESS=0 python debug_single_post.py <url>

# Quick DB query
sqlite3 playlist_archive.db "SELECT status, COUNT(*) FROM videos GROUP BY status;"

# Rebuild FTS index
sqlite3 playlist_archive.db "INSERT INTO videos_fts(videos_fts) VALUES('rebuild');"
```

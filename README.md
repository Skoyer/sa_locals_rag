<<<<<<< HEAD
# SA Locals RAG

SA Locals RAG is a pipeline that ingests Scott Adams Locals.com videos, downloads and transcribes them, analyzes the transcripts with an LLM, and builds topic‑based playlists plus a browsable web view.

---

## Environment & Assumptions

This project was originally developed and tested on:

- OS: Windows 10/11 (PowerShell terminal)
- Python: 3.11+
- FFmpeg installed and on `PATH`
- Playwright (Chromium) installed
- Optional GPU for faster Whisper / LLM runs

Some commands in this README (for example virtualenv activation) are shown in Windows form such as:

```powershell
.venv\Scripts\activate
```

On Linux/macOS, use the appropriate shell equivalents instead, for example:

```bash
source .venv/bin/activate
```


---

## Models Used

During development, the following models/tools were used:

- **Transcription**: OpenAI Whisper (local) via the `transcription/` pipeline.
- **LLM analysis (automated pipeline)**: OpenAI API models (configurable in `OPENAI_MODEL`).
- **Local experimentation**: LM Studio, running a local GGUF model (for prompt and analysis experiments outside the automated pipeline).

LM Studio and the local model were used for manual exploration, prompt design, and analysis experiments. The core pipeline in this repo can run without LM Studio; LM Studio is only needed if you want to reproduce the local experimentation setup.

---

## Quick Start

```bash
git clone https://github.com/Skoyer/sa_locals_rag.git
cd sa_locals_rag

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

cp .env.example .env   # then edit .env with your Locals + OpenAI settings

# Run the full pipeline
python run_full_pipeline.py
```

After the first run you should see:

- `playlist_archive.db` — SQLite database with videos, transcripts, and analysis.
- `data/` — downloaded videos and transcript files.
- `web/` — static HTML output.

For a more detailed walkthrough, see `docs/getting-started.md`.

---

## Project Status

This is currently a focused proof‑of‑concept built around Scott Adams’ Locals.com content. The architecture is being refactored to support additional sources (for example YouTube playlists and other creators) in the future.

---

## Documentation

More detailed documentation lives in the `docs/` folder:

- [Architecture](docs/architecture.md)
- [Getting Started](docs/getting-started.md)
- [Pipeline](docs/pipeline.md)
- [Database](docs/database.md)
- [CLI Reference](docs/cli-reference.md)
- [Web Interface](docs/web-interface.md)
- [Roadmap](docs/roadmap.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](docs/contributing.md)
=======
# Locals playlist downloader

Downloads at most one new video per hour from a playlist you have permission to archive, and stores metadata in SQLite.

## Setup

1. Create and activate the virtual environment (PowerShell):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Set the playlist URL and (for Locals.com) your login. Easiest: copy `.env.example` to `.env` and edit:

   ```powershell
   copy .env.example .env
   # Edit .env and set PLAYLIST_URL, and for Locals: LOCALS_EMAIL, LOCALS_PASSWORD
   ```

   The app loads `.env` automatically (it is in `.gitignore`, so your password is not committed). You can instead set environment variables in the shell:

   - `PLAYLIST_URL` – required (e.g. `https://locals.com/scottadams/feed?playlist=102`)
   - `LOCALS_EMAIL`, `LOCALS_PASSWORD` – required for Locals.com playlists
   - `OUTPUT_DIR` – directory for downloads (default: `./downloads`)
   - `DB_PATH` – SQLite path (default: `./playlist_archive.db`)
   - `LOCALS_COOKIES_PATH` – cookie file path (default: `./locals_cookies.txt`)

4. For Locals.com, install the browser used for login:

   ```powershell
   playwright install chromium
   ```

   If you see **"DLL load failed while importing _greenlet"** on Windows, install the [Microsoft Visual C++ Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe), then run again.

## Run

```powershell
python main.py
```

To test one download cycle without the hourly loop (e.g. debug or quick run):

```powershell
python run_once.py
```

Prints "hello" once, then every hour checks the playlist and downloads at most one new video, saving metadata (url, title, description, downloaded_at, status) to the SQLite database. The first run creates the database and table if they do not exist. For Locals.com, the first time (or when cookies are missing) the script will log in with your email/password and save cookies for later runs. Stop with Ctrl+C.

### DB vs download folder

If playlist URL counts and file counts do not match (e.g. “260 in DB” vs fewer files in `OUTPUT_DIR`), run:

```powershell
python check_downloads.py
```

It reports downloaded rows, **missing files** (DB path points nowhere), **orphan video files** (on disk but not referenced), duplicate `file_path` references, and a short **transcription readiness** summary.

## Transcription (Whisper)

After videos are downloaded (`status = downloaded` in SQLite), you can transcribe those not yet marked (`transcribed = 0`) using the separate transcription pipeline.

**Requirements**

- **FFmpeg** on `PATH` (same as for Locals HLS downloads).
- **Python deps**: `pip install -r requirements.txt` — this adds **openai-whisper**, which pulls **PyTorch** and can be several GB on disk; the first run also downloads the chosen model weights.

**Environment** (optional; same `.env` as the downloader)

- `DB_PATH` — default `./playlist_archive.db`
- `OUTPUT_DIR` — default `./downloads` (used only with `--sync-orphans`)
- `TRANSCRIPT_DIR` — where JSON transcripts and temp audio go (default `./transcriptions`)
- `WHISPER_MODEL` — e.g. `tiny`, `base`, `small`, `medium`, `large` (default `small`)

**Run**

```powershell
python -m transcription.cli
# or
python run_transcription.py
```

Process only a few files:

```powershell
python -m transcription.cli --limit 3 --model base
```

If you have video files under `OUTPUT_DIR` that were never inserted by the downloader, you can register them first (URLs like `orphan:relative/path/to/file.mp4`):

```powershell
python -m transcription.cli --sync-orphans --limit 5
```

**Behavior**

- Selects rows: `status = 'downloaded'`, `transcribed = 0`, `file_path` set; resolves paths relative to the project root like `check_downloads.py`.
- Writes `transcriptions/<video-stem>.json` with `video_url`, title, `file_path`, model, timestamps, and `whisper_result` (`text` + `segments`).
- Inserts/updates the `transcripts` table and sets `videos.transcribed = 1` on success.
- On failure, logs the error and leaves `transcribed = 0`.

**CPU vs GPU**: Whisper uses PyTorch; with a CUDA-capable GPU and a CUDA build of PyTorch, transcription is much faster. Otherwise it runs on CPU (slower).

## Help media indexer (Whisper + SQLite + FTS5)

Separate from the playlist DB: scans a media folder, transcribes with Whisper into **timestamped segments**, stores them in **`help_videos.db`**, and keeps an **FTS5** index (`transcript_segments_fts`) in sync via triggers—ready for a search UI.

**Important:** Search can only return videos you have **indexed** into `help_videos.db`. If you previously ran `index --limit 2`, only those files exist in the DB—run **`python -m help_indexer index`** (no limit) after adding downloads so every file is transcribed and searchable.

**Loose search behavior:** Multi-word queries use **AND** between terms in the same segment (e.g. `persuasion* AND ethics*`). If nothing matches, the query falls back to **OR**. If the topic appears in the **video title** but not in one segment, extra rows are added from titles that contain **all** keywords.

**Environment** (optional)

- `HELP_MEDIA_DIR` — folder to scan (default `./downloads`)
- `HELP_VIDEOS_DB` — SQLite file (default `./help_videos.db`)
- `HELP_WHISPER_MODEL` — Whisper model name (default `small`)

**CLI**

```powershell
# Create/migrate schema, transcribe every video/audio under HELP_MEDIA_DIR
python -m help_indexer index
python -m help_indexer index --limit 2 --model base

# FTS search (JSON to stdout). "loose" uses AND for multi-word, then OR fallback.
python -m help_indexer search "persuasion ethics" --limit 10
python -m help_indexer search "brain washing" --strict   # FTS5 AND all terms

# Rebuild FTS from transcript_segments if you fixed rows manually
python -m help_indexer rebuild-fts

# Optional API: GET / returns API hints; POST /index, GET /search?q=...
python -m help_indexer serve --port 8000
```

Same via `python run_help_indexer.py …`.

**HTTP API** (after `pip install -r requirements.txt`): `POST http://127.0.0.1:8000/index` with JSON body `{"limit": null}`, `GET http://127.0.0.1:8000/search?q=foo&limit=20&mode=loose` (`mode`: `loose` | `strict` | `raw`). Open `http://127.0.0.1:8000/docs` for Swagger UI.

**Requirements**: FFmpeg/ffprobe on `PATH` (for duration), Whisper/PyTorch as above.

**Programmatic search**: use `help_indexer.search.search_segments(conn, query, limit=20)` — same SQL as documented in the plan (BM25 + `snippet()`).
>>>>>>> 1dce120d66b52dbf6333ff64c26e17fc6887425a

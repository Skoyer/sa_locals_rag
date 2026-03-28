# CLI Reference

All scripts are run from the project root with `python <script>.py [options]`.

---

## Primary Scripts

### `run_full_pipeline.py`

Runs all pipeline stages end-to-end: authentication → playlist fetch → download → transcription → LLM analysis → web generation.

```bash
python run_full_pipeline.py
```

| Flag | Description |
|---|---|
| *(none yet)* | Currently runs all stages unconditionally |

---

### `main.py`

Downloads new videos from the configured playlist URL. Checks the database for already-downloaded URLs and skips them.

```bash
python main.py
```

---

### `run_transcription.py`

Runs Whisper transcription on all downloaded-but-not-yet-transcribed videos.

```bash
python run_transcription.py
```

---

### `run_once.py`

Runs a single pass of the download stage (useful for cron or scheduled invocations).

```bash
python run_once.py
```

---

### `sa_rag_chat.py`

Interactive command-line RAG chat against the transcript database. Accepts a question, retrieves relevant transcripts via FTS5, and sends context + question to the OpenAI API.

```bash
python sa_rag_chat.py
```

**Runtime commands**:
- Type a question and press Enter
- Type `quit` or `exit` to stop
- Type `help` to see usage hints

---

## Maintenance & Utility Scripts

### `check_progress.py`

Prints a summary of the current database state: total videos, downloaded, transcribed, analyzed.

```bash
python check_progress.py
```

**Sample output**:
```
Total videos:    312
Downloaded:      298
Transcribed:     245
LLM analyzed:    201
Failed:           14
```

---

### `check_downloads.py`

Detailed check of all database entries vs. files on disk. Reports:
- Videos in DB with status `downloaded` but no file on disk
- Files on disk not referenced in the DB
- Duplicate file path entries

```bash
python check_downloads.py
```

| Flag | Default | Description |
|---|---|---|
| `--fix` | off | Auto-update DB records to match disk state |
| `--verbose` | off | Print each file path checked |

---

### `export_csv.py`

Exports the full `videos` table to `playlist_archive.csv`.

```bash
python export_csv.py
```

---

### `retry_failed_hls.py`

Re-fetches stream URLs and retries download for all videos with `status = 'failed'`.

```bash
python retry_failed_hls.py
```

Options:

| Flag | Description |
|---|---|
| `--limit N` | Only retry the first N failed videos |
| `--dry-run` | Print what would be retried without downloading |

---

### `redownload_duplicate_failed.py`

Finds videos where the `file_path` in the DB is a duplicate or points to a missing file, and re-downloads them.

```bash
python redownload_duplicate_failed.py
```

---

### `fix_duplicate_filepaths.py`

Database-only maintenance: finds duplicate `file_path` values in the `videos` table and resolves them (keeps the entry with the file that exists on disk).

```bash
python fix_duplicate_filepaths.py
```

---

### `debug_single_post.py`

Fetches and downloads a single Locals.com post URL, printing verbose debug output. Useful for diagnosing failures on individual videos.

```bash
python debug_single_post.py <locals-post-url>
```

---

### `run_help_indexer.py`

Runs the help document indexer (indexes external markdown or text help files into the RAG context).

```bash
python run_help_indexer.py
```

---

## Transcription CLI

`transcription/cli.py` exposes a dedicated entry point:

```bash
python -m transcription.cli [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--model MODEL` | `base` | Whisper model size |
| `--device DEVICE` | `cpu` | `cpu` or `cuda` |
| `--limit N` | unlimited | Max number of videos to transcribe |
| `--video-url URL` | all | Transcribe a specific video by URL |
| `--sync-only` | off | Only sync existing transcript files to DB; do not run Whisper |

**Examples**:

```bash
# Transcribe all pending videos using the small model on GPU
python -m transcription.cli --model small --device cuda

# Transcribe only 10 videos (useful for testing)
python -m transcription.cli --limit 10

# Sync existing transcript files to the database without re-transcribing
python -m transcription.cli --sync-only
```

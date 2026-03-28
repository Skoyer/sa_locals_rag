# Module API Reference

This document describes the public functions of each Python module.

---

## `locals_auth.py`

Handles automated login to Locals.com via Playwright.

### `login_and_save_cookies(email, password, cookies_path, *, headless=True) -> bool`

Launches a Chromium browser, logs in with the given credentials, and saves session cookies to `cookies_path` in Netscape format.

**Parameters**:
- `email` — Locals.com account email
- `password` — Locals.com account password
- `cookies_path` — `Path` or `str` where cookie file is written
- `headless` — Whether to run headless (default `True`)

**Returns**: `True` on success, `False` on failure.

---

## `locals_fetcher.py`

### `get_playlist_video_urls(playlist_url, cookies_path, *, timeout_ms=60000) -> list[str]`

Scrapes a Locals.com playlist page with infinite scroll to return all post URLs in order.

### `get_video_info_and_stream_url(video_page_url, cookies_path, *, timeout_ms=30000) -> tuple[str, str, str | None]`

Returns `(title, description, stream_url)` for a single video post. `stream_url` may be an HLS `.m3u8` or direct `.mp4` URL, or `None` if extraction failed.

### `download_locals_hls_with_ffmpeg(stream_url, output_path, cookies_path) -> bool`

Downloads an HLS stream using `ffmpeg -c copy` with cookies injected as a request header.

### `download_locals_video_with_ytdlp(video_url, output_dir, cookies_path, outtmpl) -> tuple[str, str] | None`

Downloads a video using `yt-dlp`. Returns `(title, description)` or `None` on failure.

### `download_locals_stream_with_requests(stream_url, output_path, cookies_path) -> bool`

Downloads a direct stream URL using `requests` with cookies loaded from the Netscape file.

### `ensure_locals_cookies() -> bool`

Checks whether a valid cookie file exists; if not (or if the file is too small), triggers `login_and_save_cookies()`.

---

## `db.py`

### `init_db(path="playlist_archive.db") -> None`

Creates the database and all tables/triggers/indexes if they do not exist. Also runs any pending column migrations.

### `get_downloaded_urls(conn) -> set[str]`

Returns the set of URLs where `status = 'downloaded'`.

### `insert_video(conn, url, title, description, status, file_path=None, posted_at=None) -> None`

Inserts or updates a video row. Preserves all LLM/RAG analysis columns on conflict.

### `insert_transcript(conn, video_url, transcript_path, model_name, created_at) -> None`

Inserts or updates a transcript row.

### `mark_video_transcribed(conn, video_url) -> None`

Sets `transcribed = 1` for a video URL.

---

## `transcription/audio.py`

### `extract_audio(video_path, output_wav_path) -> bool`

Uses `ffmpeg` to extract a 16 kHz mono WAV file from the given video. Returns `True` on success.

---

## `transcription/whisper_runner.py`

### `transcribe(wav_path, model_name="base", device="cpu") -> str`

Loads the specified Whisper model and transcribes the WAV file. Returns the full transcript as a string.

---

## `transcription/pipeline.py`

### `run_transcription_pipeline(limit=None, video_url=None, model="base", device="cpu") -> None`

Main orchestrator: queries the DB for un-transcribed videos, extracts audio, runs Whisper, saves transcript files, and updates the DB.

---

## `transcription/sync.py`

### `sync_transcripts_to_db(transcript_dir, db_path) -> int`

Scans `transcript_dir` for `.txt` files and inserts any that are missing from the `transcripts` table. Returns the count of newly synced entries.

---

## `pipeline/llm_pipeline.py`

### `run_llm_pipeline(limit=None, force=False) -> None`

Processes all transcribed-but-not-yet-analyzed videos through the OpenAI API. Set `force=True` to re-analyze already-analyzed videos.

### `analyze_transcript(transcript_text, video_url, model="gpt-4o") -> dict`

Sends a single transcript to the LLM and returns a dictionary of extracted fields.

---

## `config.py`

Loads all environment variables from `.env` and exposes them as module-level constants:

```python
import config

print(config.LOCALS_EMAIL)
print(config.OPENAI_API_KEY)
print(config.DB_PATH)
```

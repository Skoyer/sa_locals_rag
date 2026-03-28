# Troubleshooting

---

## Authentication Issues

### `Cookie file missing or too small`

The cookie file is either missing or corrupted. If `LOCALS_EMAIL` and `LOCALS_PASSWORD` are set, the system will automatically re-login. If not:

```bash
# Manually trigger login
python -c "from locals_auth import login_and_save_cookies; login_and_save_cookies('you@email.com', 'pass', 'locals_cookies.txt', headless=False)"
```

Set `LOCALS_HEADLESS=0` to watch the browser and confirm login is completing.

### Cookies expire quickly

Locals.com sessions can expire. Re-run the login step before long pipeline runs, or schedule it periodically.

---

## Download Failures

### `status = 'failed'` in the database

Run the retry script:
```bash
python retry_failed_hls.py
```

If failures persist, enable debug output to see what's happening:
```bash
LOCALS_DEBUG_HTML=1 python debug_single_post.py <post-url>
```

This saves the raw HTML to `post_page_debug.html` for inspection.

### `ffmpeg: command not found`

Install ffmpeg and ensure it is on your `PATH`:
```bash
which ffmpeg   # Linux/macOS
where ffmpeg   # Windows
```

### HLS download succeeds but file is 0 bytes

The `vt=` JWT token in the stream URL has likely expired. Re-fetch the stream URL:
```bash
python retry_failed_hls.py --limit 1
```

### `playwright._impl._errors.Error: Chromium ... not found`

```bash
playwright install chromium
```

---

## Transcription Issues

### Whisper is very slow

- Use a smaller model: `WHISPER_MODEL=tiny` or `WHISPER_MODEL=base`
- Enable GPU: `WHISPER_DEVICE=cuda` (requires CUDA-compatible GPU and `torch` with CUDA)

### Transcription produces garbage text

- The audio quality may be too poor for the selected model. Try `WHISPER_MODEL=medium`.
- Verify the WAV file is valid: `ffprobe data/transcripts/some_file.wav`

### `CUDA out of memory`

Reduce the model size or switch to CPU: `WHISPER_DEVICE=cpu`.

---

## LLM Analysis Issues

### `openai.AuthenticationError`

Check that `OPENAI_API_KEY` is correctly set in `.env` and the key is valid.

### LLM analysis is slow / expensive

- Use `gpt-3.5-turbo` instead of `gpt-4o` (`OPENAI_MODEL=gpt-3.5-turbo`) for lower cost
- Add `--limit N` to process only N videos at a time

### LLM returns malformed JSON

The `llm_pipeline.py` includes retry logic. If analysis consistently fails for a video, check that its transcript file is not empty:
```bash
wc -c data/transcripts/<video_id>.txt
```

---

## Database Issues

### `database is locked`

SQLite does not support concurrent writers. Ensure only one pipeline process is running at a time.

### `no such column: <column_name>`

Run any pipeline script to trigger auto-migration:
```bash
python check_progress.py
```

`db.py` will detect missing columns and add them via `ALTER TABLE`.

### FTS search returns no results

Rebuild the FTS index:
```bash
sqlite3 playlist_archive.db "INSERT INTO videos_fts(videos_fts) VALUES('rebuild');"
```

---

## Web / HTML Output

### Static page is blank or missing videos

Ensure the LLM pipeline has been run and videos have `summary_text` populated:
```sql
SELECT COUNT(*) FROM videos WHERE summary_text IS NOT NULL;
```

### Word cloud images missing

The `wordclouds/` directory may need to be regenerated. Run the NLP/clustering step directly.

---

## Debugging Tips

| Env Var | Effect |
|---|---|
| `LOCALS_HEADLESS=0` | Show browser window during Playwright operations |
| `LOCALS_DEBUG_HTML=1` | Save raw HTML to debug files in the project root |
| `LOCALS_DEBUG_API=1` | Log Locals API probe responses |
| `LOCALS_ENABLE_API_PROBE=1` | Enable direct API probing (usually blocked by Cloudflare) |

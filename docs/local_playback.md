# Local video playback

## Problem

Pipeline downloads Locals.com videos to disk (`OUTPUT_DIR`, default `./downloads`) and stores
the path in SQLite `videos.file_path` (often a Windows absolute path like
`C:\Users\...\downloads\post-123.mp4`). Topic Browser and web2 previously linked every
card to the Locals.com URL, so watching required the website even when the file was local.

Browsers cannot play arbitrary `file:///C:/...` paths for security reasons.

## Approach

1. **Export flag** — `web/summary_page.py` sets `has_local_file` when the stored path (or the
   same basename under `OUTPUT_DIR`) exists at export time. Absolute C: paths are **not**
   embedded in `lessons.json` / `data.js`.
2. **Media server** — `python -m local_media serve` (default port **8010**) looks up
   `transcript_id` → `videos.file_path` and streams the file (`GET /media/video/{id}`) with
   correct MIME type. Path resolution:
   - absolute path as stored (works on the original Windows machine);
   - path relative to the repo root;
   - basename under `OUTPUT_DIR` (remaps missing C: paths after copy/sync).
3. **UI** — Topic Browser (primary) and web2 open an in-app `<video>` player for local files
   instead of navigating to Locals.com. Vite proxies `/media` → `http://127.0.0.1:8010`.

## Run on Windows (C: drive library)

```powershell
python web/summary_page.py
python -m local_media serve --port 8010
cd topic-browser; npm run dev
```

Open http://localhost:5173 — cards with a resolvable download show **Watch local**.

Ensure `DB_PATH` and `OUTPUT_DIR` in `.env` match the machine that holds the files.

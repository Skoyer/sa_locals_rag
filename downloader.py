"""Download at most one new video per run from a playlist (yt-dlp or Locals.com)."""
import os
import re
import sqlite3

import yt_dlp

import config
import db


def _entry_url(entry: dict) -> str | None:
    """Get the canonical video URL from a playlist entry."""
    return entry.get("url") or entry.get("webpage_url")


def _is_locals_url(url: str) -> bool:
    """True if the URL is a Locals.com playlist or video page."""
    return "locals.com" in (url or "").lower()


def _locals_post_id(video_url: str) -> str | None:
    """Extract numeric post id from Locals URL: feed?post=12345."""
    m = re.search(r"post=(\d+)", video_url or "")
    return m.group(1) if m else None


def _log(msg: str) -> None:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}")


def _dbg(hypothesis_id: str, message: str, data: dict) -> None:
    """Write a small NDJSON debug log (no secrets)."""
    import json
    import time as _time

    try:
        payload = {
            "sessionId": "210768",
            "runId": os.environ.get("DBG_RUN_ID", "run"),
            "hypothesisId": hypothesis_id,
            "location": "downloader.py",
            "message": message,
            "data": data,
            "timestamp": int(_time.time() * 1000),
        }
        with open("debug-210768.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _download_one_locals(
    conn: sqlite3.Connection,
    playlist_url: str,
    output_dir: str,
) -> None:
    """Handle one run for a Locals.com playlist: ensure cookies, list, pick one, download, insert."""
    import locals_fetcher

    _log("Using Locals.com (playlist requires login).")
    if not locals_fetcher.ensure_locals_cookies():
        _log("FAILED: LOCALS_EMAIL and LOCALS_PASSWORD must be set, or login failed. Check credentials.")
        return
    _log("Locals auth OK (cookies ready).")
    cookies_path = config.LOCALS_COOKIES_PATH
    downloaded_urls = db.get_downloaded_urls(conn)
    n_done = len(downloaded_urls)
    os.makedirs(output_dir, exist_ok=True)

    _log("Fetching playlist...")
    urls = locals_fetcher.get_playlist_video_urls(playlist_url, cookies_path)
    _log(f"Playlist: {len(urls)} video link(s) found, {n_done} already in DB.")
    max_attempts = int(os.environ.get("LOCALS_MAX_CANDIDATES_PER_RUN", "8"))
    attempted = 0

    for video_url in urls:
        if not video_url or video_url in downloaded_urls:
            continue
        attempted += 1
        _log(f"Picking candidate: {video_url[:80]}...")
        _dbg("H1", "candidate_start", {"url": video_url, "attempt": attempted, "max": max_attempts})

        # Try yt-dlp with cookies first
        outtmpl = os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s")
        result = locals_fetcher.download_locals_video_with_ytdlp(
            video_url, output_dir, cookies_path, outtmpl
        )
        if result:
            title, description = result
            db.insert_video(conn, video_url, title, description, "downloaded")
            _log(f"SUCCESS: Downloaded and saved to DB: {title or video_url}")
            _dbg("H1", "candidate_success_ytdlp_page", {"url": video_url, "title": (title or "")[:120]})
            return

        # Fallback: get stream URL and download with yt-dlp (HLS) or requests (direct)
        _log("yt-dlp direct failed; trying stream URL...")
        title, description, stream_url = locals_fetcher.get_video_info_and_stream_url(
            video_url, cookies_path
        )
        _dbg(
            "H2",
            "stream_url_result",
            {
                "url": video_url,
                "stream_prefix": (stream_url or "")[:20],
                "is_m3u8": bool(stream_url and ".m3u8" in stream_url),
                "is_blob": bool(stream_url and stream_url.startswith("blob:")),
                "has_stream": bool(stream_url),
            },
        )

        # If we only got a blob URL, mark it and move on immediately.
        if stream_url and stream_url.startswith("blob:"):
            db.insert_video(conn, video_url, title, description, "failed: blob stream")
            _log("FAILED: stream is blob: URL (browser-only). Trying next video.")
            if attempted >= max_attempts:
                return
            continue
        if stream_url and ".m3u8" in stream_url:
            safe_title = re.sub(r'[<>:"/\\|?*]', "_", title or "video")[:80]
            post_id = _locals_post_id(video_url)
            suffix = f" [post={post_id}]" if post_id else ""
            filename = f"{safe_title}{suffix}.mp4"
            out_path = os.path.join(output_dir, filename)
            try:
                opts = {
                    "outtmpl": out_path,
                    "cookiefile": cookies_path,
                    "quiet": False,
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([stream_url])
                db.insert_video(conn, video_url, title, description, "downloaded", file_path=out_path)
                _log(f"SUCCESS: Downloaded (HLS, yt-dlp) and saved to DB: {title or video_url}")
                _dbg("H1", "candidate_success_hls", {"url": video_url, "file_path": out_path})
                return
            except Exception as e:
                _log(f"yt-dlp HLS failed: {e}; trying ffmpeg...")
            if locals_fetcher.download_locals_hls_with_ffmpeg(stream_url, out_path, cookies_path):
                db.insert_video(conn, video_url, title, description, "downloaded", file_path=out_path)
                _log(f"SUCCESS: Downloaded (HLS, ffmpeg) and saved to DB: {title or video_url}")
                _dbg("H1", "candidate_success_ffmpeg", {"url": video_url, "file_path": out_path})
                return
            db.insert_video(conn, video_url, title, description, f"failed: HLS download: {e!s}", file_path=out_path)
            _log("FAILED: HLS download (yt-dlp and ffmpeg failed).")
            if attempted >= max_attempts:
                return
            continue

        if stream_url:
            safe_title = re.sub(r'[<>:"/\\|?*]', "_", title or "video")[:80]
            post_id = _locals_post_id(video_url)
            suffix = f" [post={post_id}]" if post_id else ""
            filename = f"{safe_title}{suffix}.mp4"
            out_path = os.path.join(output_dir, filename)
            # Prefer yt-dlp for direct URLs too (handles headers/auth better than raw requests)
            try:
                opts = {
                    "outtmpl": out_path,
                    "cookiefile": cookies_path,
                    "quiet": False,
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([stream_url])
                db.insert_video(conn, video_url, title, description, "downloaded", file_path=out_path)
                _log(f"SUCCESS: Downloaded (direct, yt-dlp) to {out_path} and saved to DB.")
                _dbg("H1", "candidate_success_direct_ytdlp", {"url": video_url, "file_path": out_path})
                return
            except Exception as e:
                _log(f"yt-dlp direct stream failed: {e}; trying requests...")
            if locals_fetcher.download_locals_stream_with_requests(stream_url, out_path, cookies_path):
                db.insert_video(conn, video_url, title, description, "downloaded", file_path=out_path)
                _log(f"SUCCESS: Downloaded (direct, requests) to {out_path} and saved to DB.")
                _dbg("H1", "candidate_success_direct_requests", {"url": video_url, "file_path": out_path})
                return
            db.insert_video(conn, video_url, title, description, "failed: direct stream download")
            _log("FAILED: Direct stream download failed. Trying next video.")
            if attempted >= max_attempts:
                return
            continue

        db.insert_video(conn, video_url, title, description, "failed: no stream URL")
        _log("FAILED: Could not get stream URL for this video. Trying next video.")
        if attempted >= max_attempts:
            return

    _log("No downloadable video found this run (candidates exhausted).")


def download_one_if_any(
    conn: sqlite3.Connection,
    playlist_url: str,
    output_dir: str,
) -> None:
    """
    List playlist, pick the first video not in the DB, download it, and insert metadata.
    If no new video or PLAYLIST_URL is unset, skip (log and return).
    Supports yt-dlp-compatible URLs and Locals.com (with LOCALS_EMAIL/LOCALS_PASSWORD).
    """
    if not playlist_url:
        _log("PLAYLIST_URL not set; skipping download.")
        return

    if _is_locals_url(playlist_url):
        _download_one_locals(conn, playlist_url, output_dir)
        return

    downloaded_urls = db.get_downloaded_urls(conn)
    os.makedirs(output_dir, exist_ok=True)

    list_opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(list_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    entries = info.get("entries") or []

    video_url = None
    for entry in entries:
        if entry is None:
            continue
        url = _entry_url(entry)
        if url and url not in downloaded_urls:
            video_url = url
            break

    if not video_url:
        _log("No new video in playlist (all already in DB).")
        return

    _log(f"Downloading: {video_url[:80]}...")
    outtmpl = os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s")
    download_opts = {
        "outtmpl": outtmpl,
        "quiet": False,
    }
    try:
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            full_info = ydl.extract_info(video_url, download=True)
        title = (full_info or {}).get("title") or ""
        description = (full_info or {}).get("description") or ""
        db.insert_video(conn, video_url, title, description, "downloaded")
        _log(f"SUCCESS: Downloaded and saved to DB: {title}")
    except Exception as e:
        db.insert_video(
            conn,
            video_url,
            "",
            "",
            f"failed: {e!s}",
        )
        _log(f"FAILED: {e}")

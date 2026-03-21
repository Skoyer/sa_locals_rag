"""
Re-download URLs that were marked as:
  failed: duplicate file_path

This script will:
  - ensure Locals cookies exist
  - for each URL, try Locals capture + download (same as main pipeline)
  - update DB status and file_path

Usage:
  .\\.venv\\Scripts\\python.exe redownload_duplicate_failed.py
"""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import config
import db
import locals_fetcher


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {msg}")


def _locals_post_id(url: str) -> str | None:
    m = re.search(r"post=(\d+)", url or "")
    return m.group(1) if m else None


def _safe_filename(title: str) -> str:
    t = re.sub(r'[<>:"/\\|?*]', "_", title or "video").strip()
    t = t if t else "video"
    return t[:120]


def _build_out_path(output_dir: str, url: str, title: str) -> str:
    post_id = _locals_post_id(url)
    base = _safe_filename(title)
    suffix = f" [post={post_id}]" if post_id else ""
    filename = f"{base}{suffix}.mp4"
    return os.path.join(output_dir, filename)


def main() -> int:
    project_root = Path(__file__).resolve().parent
    db_path = Path(config.DB_PATH)
    if not db_path.is_absolute():
        db_path = project_root / db_path

    db.init_db(str(db_path))
    conn = sqlite3.connect(str(db_path))
    try:
        # Only handle Locals URLs (playlist posts)
        cur = conn.execute(
            """
            SELECT url
            FROM videos
            WHERE status LIKE 'failed: duplicate file_path (%'
            OR status='failed: duplicate file_path'
            """
        )
        rows = cur.fetchall()
        urls = [row[0] for row in rows if row and isinstance(row[0], str) and "locals.com" in row[0].lower()]
        if not urls:
            log("No duplicate-marked Locals URLs found; nothing to do.")
            return 0

        output_dir = config.OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        if not locals_fetcher.ensure_locals_cookies():
            log("FAILED: Locals login/cookies missing. Check LOCALS_EMAIL and LOCALS_PASSWORD.")
            return 1

        log(f"Re-downloading {len(urls)} duplicate-marked URL(s)...")
        cookies_path = config.LOCALS_COOKIES_PATH

        for i, url in enumerate(urls, start=1):
            log(f"[{i}/{len(urls)}] URL: {url}")
            try:
                title, description, stream_url = locals_fetcher.get_video_info_and_stream_url(url, cookies_path)
                if not stream_url:
                    db.insert_video(conn, url, title or "", description or "", "failed: no stream URL", file_path=None)
                    log(" -> FAILED: no stream URL")
                    continue

                out_path = _build_out_path(output_dir, url, title or "video")

                # Prefer HLS when possible
                if ".m3u8" in stream_url:
                    # Mirror main pipeline: yt-dlp first, then ffmpeg.
                    try:
                        import yt_dlp

                        opts = {"outtmpl": out_path, "cookiefile": cookies_path, "quiet": False}
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            ydl.download([stream_url])
                        db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
                        log(f" -> SUCCESS (HLS yt-dlp): {out_path}")
                        continue
                    except Exception as e:
                        log(f" -> yt-dlp HLS failed: {e}; trying ffmpeg...")

                    ok = locals_fetcher.download_locals_hls_with_ffmpeg(stream_url, out_path, cookies_path)
                    if ok:
                        db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
                        log(f" -> SUCCESS (HLS ffmpeg): {out_path}")
                    else:
                        db.insert_video(conn, url, title or "", description or "", "failed: HLS download", file_path=out_path)
                        log(" -> FAILED: HLS download")
                    continue

                # Direct stream: use yt-dlp if available, else requests
                try:
                    import yt_dlp

                    opts = {"outtmpl": out_path, "cookiefile": cookies_path, "quiet": False}
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([stream_url])
                    db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
                    log(f" -> SUCCESS (direct yt-dlp): {out_path}")
                except Exception as e:
                    ok = locals_fetcher.download_locals_stream_with_requests(stream_url, out_path, cookies_path)
                    if ok:
                        db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
                        log(f" -> SUCCESS (direct requests): {out_path}")
                    else:
                        db.insert_video(conn, url, title or "", description or "", f"failed: direct download ({e!s})", file_path=out_path)
                        log(f" -> FAILED: direct download: {e!s}")

            except Exception as e:
                db.insert_video(conn, url, "", "", f"failed: exception ({e!s})", file_path=None)
                log(f" -> FAILED: exception: {e!s}")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())


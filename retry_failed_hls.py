"""
Retry Locals URLs that previously failed HLS download.

Usage:
  .\\.venv\\Scripts\\python.exe retry_failed_hls.py
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
    return (t[:120] if t else "video")


def _build_out_path(output_dir: str, url: str, title: str) -> str:
    post_id = _locals_post_id(url)
    base = _safe_filename(title)
    suffix = f" [post={post_id}]" if post_id else ""
    return os.path.join(output_dir, f"{base}{suffix}.mp4")


def main() -> int:
    project_root = Path(__file__).resolve().parent
    db_path = Path(config.DB_PATH)
    if not db_path.is_absolute():
        db_path = project_root / db_path

    db.init_db(str(db_path))
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            """
            SELECT url
            FROM videos
            WHERE status='failed: HLS download'
            """
        )
        rows = cur.fetchall()
        urls = [row[0] for row in rows if row and isinstance(row[0], str) and "locals.com" in row[0].lower()]

        if not urls:
            log("No rows with status='failed: HLS download' found.")
            return 0

        output_dir = config.OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        if not locals_fetcher.ensure_locals_cookies():
            log("FAILED: Locals login/cookies missing. Check LOCALS_EMAIL and LOCALS_PASSWORD.")
            return 1

        cookies_path = config.LOCALS_COOKIES_PATH
        log(f"Retrying HLS for {len(urls)} URL(s)...")

        for i, url in enumerate(urls, start=1):
            log(f"[{i}/{len(urls)}] {url}")
            try:
                title, description, stream_url = locals_fetcher.get_video_info_and_stream_url(url, cookies_path)
                if not stream_url:
                    db.insert_video(conn, url, title or "", description or "", "failed: no stream URL (retry-hls)", file_path=None)
                    log(" -> FAILED: no stream URL")
                    continue

                out_path = _build_out_path(output_dir, url, title or "video")

                if ".m3u8" not in stream_url:
                    db.insert_video(conn, url, title or "", description or "", f"failed: stream not m3u8 (retry-hls)", file_path=out_path)
                    log(" -> FAILED: stream not m3u8")
                    continue

                # Try yt-dlp with cookies first.
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

                if locals_fetcher.download_locals_hls_with_ffmpeg(stream_url, out_path, cookies_path):
                    db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
                    log(f" -> SUCCESS (HLS ffmpeg): {out_path}")
                else:
                    db.insert_video(conn, url, title or "", description or "", "failed: HLS download", file_path=out_path)
                    log(" -> FAILED: HLS download")

            except Exception as e:
                db.insert_video(conn, url, "", "", f"failed: exception ({e!s})", file_path=None)
                log(f" -> FAILED: exception {e!s}")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())


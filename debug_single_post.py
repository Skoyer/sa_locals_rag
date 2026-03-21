"""Debug a single Locals post URL (no playlist scrolling)."""

import os
import re
import sqlite3
from datetime import datetime, timezone

import config
import db
import locals_fetcher


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {msg}")


def _safe_filename(title: str) -> str:
    t = re.sub(r'[<>:"/\\|?*]', "_", title or "video").strip()
    return (t[:120] if t else "video") + ".mp4"


def _locals_post_id(url: str) -> str | None:
    m = re.search(r"post=(\d+)", url or "")
    return m.group(1) if m else None


def main() -> int:
    url = None
    if len(os.sys.argv) >= 2:
        url = os.sys.argv[1].strip()
    url = url or os.environ.get("LOCALS_TEST_POST_URL") or ""

    if not url:
        log("ERROR: Provide a Locals post URL via arg or LOCALS_TEST_POST_URL.")
        log('Example: python debug_single_post.py "https://locals.com/scottadams/feed?post=5751847"')
        return 2

    log("--- Debug single Locals post ---")
    db.init_db(config.DB_PATH)
    conn = sqlite3.connect(config.DB_PATH)
    try:
        if not locals_fetcher.ensure_locals_cookies():
            log("FAILED: Locals login failed (check LOCALS_EMAIL / LOCALS_PASSWORD).")
            return 1

        log(f"Post URL: {url}")
        cookies_path = config.LOCALS_COOKIES_PATH

        # Capture stream URL via Playwright (headed if LOCALS_HEADLESS=0)
        title, description, stream_url = locals_fetcher.get_video_info_and_stream_url(url, cookies_path)
        log(f"Title: {title[:120] if title else '(none)'}")
        log(f"Stream URL captured: {'YES' if stream_url else 'NO'}")
        if not stream_url:
            db.insert_video(conn, url, title or "", description or "", "failed: no stream URL (debug)")
            return 1

        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        post_id = _locals_post_id(url)
        base = _safe_filename(title).replace(".mp4", "")
        suffix = f" [post={post_id}]" if post_id else ""
        out_path = os.path.join(config.OUTPUT_DIR, f"{base}{suffix}.mp4")

        if ".m3u8" in stream_url:
            log("Downloading HLS...")
            # Match main pipeline: try yt-dlp with cookies first, then ffmpeg.
            try:
                import yt_dlp

                opts = {"outtmpl": out_path, "cookiefile": cookies_path, "quiet": False}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([stream_url])
                db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
                log(f"SUCCESS: Downloaded HLS with yt-dlp to {out_path}")
                return 0
            except Exception as e:
                log(f"yt-dlp HLS failed: {e}; trying ffmpeg...")
            if locals_fetcher.download_locals_hls_with_ffmpeg(stream_url, out_path, cookies_path):
                db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
                log(f"SUCCESS: Downloaded HLS with ffmpeg to {out_path}")
                return 0
            db.insert_video(conn, url, title or "", description or "", "failed: ffmpeg HLS (debug)", file_path=out_path)
            log("FAILED: HLS download failed (yt-dlp and ffmpeg).")
            return 1

        log("Downloading direct stream...")
        try:
            import yt_dlp

            opts = {"outtmpl": out_path, "cookiefile": cookies_path, "quiet": False}
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([stream_url])
            db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
            log(f"SUCCESS: Downloaded (direct, yt-dlp) to {out_path}")
            return 0
        except Exception as e:
            log(f"yt-dlp direct stream failed: {e}; trying requests...")
        if locals_fetcher.download_locals_stream_with_requests(stream_url, out_path, cookies_path):
            db.insert_video(conn, url, title or "", description or "", "downloaded", file_path=out_path)
            log(f"SUCCESS: Downloaded (direct, requests) to {out_path}")
            return 0

        db.insert_video(conn, url, title or "", description or "", "failed: direct stream (debug)")
        log("FAILED: direct stream download failed.")
        return 1
    finally:
        conn.close()
        log("--- Done ---")


if __name__ == "__main__":
    raise SystemExit(main())


"""
Compare SQLite DB rows vs actual files in ./downloads.

Usage:
  python check_downloads.py
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import config

# Match transcription/audio.py — DB may reference these; MP4-only counts confuse users.
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".m4v", ".mov", ".avi"}


def _video_files_in_dir(d: Path, *, recursive: bool) -> list[Path]:
    if not d.is_dir():
        return []
    if recursive:
        return sorted(
            p
            for p in d.rglob("*")
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        )
    return sorted(
        p
        for p in d.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    )


def _abs_path(project_root: Path, p: str | None) -> Path | None:
    if not p:
        return None
    path = Path(p)
    if path.is_absolute():
        return path
    # stored paths are often relative like "./downloads\\file.mp4"
    return (project_root / path).resolve()


def main() -> int:
    project_root = Path(__file__).resolve().parent
    db_path = Path(config.DB_PATH)
    downloads_dir = Path(config.OUTPUT_DIR)

    if not db_path.is_absolute():
        db_path = (project_root / db_path).resolve()
    if not downloads_dir.is_absolute():
        downloads_dir = (project_root / downloads_dir).resolve()

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM videos")
        total_rows = int(cur.fetchone()[0])

        cur = conn.execute("SELECT COUNT(*) FROM videos WHERE status='downloaded'")
        downloaded_rows = int(cur.fetchone()[0])

        cur = conn.execute("SELECT COUNT(*) FROM videos WHERE status LIKE 'failed:%'")
        failed_rows = int(cur.fetchone()[0])

        cur = conn.execute("SELECT COUNT(*) FROM videos WHERE file_path IS NOT NULL AND status='downloaded'")
        downloaded_rows_with_file_path = int(cur.fetchone()[0])

        cur = conn.execute(
            "SELECT url, title, file_path FROM videos WHERE status='downloaded' AND file_path IS NULL"
        )
        downloaded_rows_no_file_path = cur.fetchall()
        downloaded_rows_no_file_path_count = len(downloaded_rows_no_file_path)

        # Check which downloaded rows point to an existing file
        cur = conn.execute("SELECT url, title, file_path FROM videos WHERE status='downloaded' AND file_path IS NOT NULL")
        rows_with_file_path = cur.fetchall()

        missing_files = []
        referenced_files = set()
        file_to_urls: dict[Path, list[tuple[str, str]]] = {}
        for url, title, file_path in rows_with_file_path:
            abs_fp = _abs_path(project_root, file_path)
            if abs_fp is None:
                continue
            if abs_fp.exists():
                referenced_files.add(abs_fp)
                file_to_urls.setdefault(abs_fp, []).append((url, title or ""))
            else:
                missing_files.append((url, title, str(abs_fp)))

        # Scan filesystem (all common video types)
        video_files_recursive = _video_files_in_dir(downloads_dir, recursive=True)
        video_files_top = _video_files_in_dir(downloads_dir, recursive=False)
        mp4_only_recursive = sorted(downloads_dir.glob("**/*.mp4"))

        other_files = [
            p
            for p in downloads_dir.glob("**/*")
            if p.is_file() and p.suffix.lower() not in VIDEO_EXTENSIONS
        ]

        video_count_recursive = len(video_files_recursive)
        video_count_top = len(video_files_top)

        # Orphan files on disk (not referenced by DB)
        orphans = [p for p in video_files_recursive if p.resolve() not in referenced_files]

        print("=== DB vs Disk ===")
        print(f"Project root: {project_root}")
        print(f"DB: {db_path}")
        print(f"Downloads dir: {downloads_dir}")
        print("")
        print(f"videos rows: {total_rows}")
        print(f"downloaded rows: {downloaded_rows}")
        print(f"failed rows: {failed_rows}")
        print("")
        unique_referenced_files = len(referenced_files)
        duplicate_file_paths = {fp: urls for fp, urls in file_to_urls.items() if len(urls) > 1}
        duplicate_count = len(duplicate_file_paths)

        print(f"downloaded rows with file_path: {downloaded_rows_with_file_path}")
        print(f"downloaded rows with NULL file_path: {downloaded_rows_no_file_path_count}")
        print("")
        print(f"Video files on disk (recursive, {', '.join(sorted(VIDEO_EXTENSIONS))}): {video_count_recursive}")
        print(f"Video files in OUTPUT_DIR top-level only: {video_count_top}")
        print(f"MP4 files on disk (recursive, legacy metric): {len(mp4_only_recursive)}")
        print(f"Other files on disk under OUTPUT_DIR (non-video): {len(other_files)}")
        print(f"Unique file_path referenced by DB: {unique_referenced_files}")
        print(f"Duplicate file_path references (N videos share one file): {duplicate_count}")
        print(f"Orphan video files (on disk, not referenced by any DB file_path): {len(orphans)}")
        print(f"Missing files (DB status=downloaded + file_path set, file not on disk): {len(missing_files)}")
        print("")

        cur = conn.execute(
            """
            SELECT COUNT(*) FROM videos
            WHERE status = 'downloaded' AND transcribed = 0 AND file_path IS NOT NULL
            """
        )
        transcribe_candidates = int(cur.fetchone()[0])
        on_disk_and_downloaded = downloaded_rows_with_file_path - len(missing_files)
        print("=== Transcription readiness ===")
        print(
            f"Downloaded rows with file_path that exist on disk: {on_disk_and_downloaded} "
            f"(same as 'unique referenced' if no duplicates)"
        )
        print(f"Rows eligible for transcription pipeline (downloaded, transcribed=0, file_path set): {transcribe_candidates}")
        print(
            "You have 'all files you need' when: missing_files=0, orphans=0 (or orphans acknowledged), "
            "and downloaded_rows_no_file_path=0 if you require paths for every download."
        )
        print("")

        # Print a short actionable list
        limit = 25
        if missing_files:
            print(f"--- Missing (up to {limit}) ---")
            for i, (url, title, abs_fp) in enumerate(missing_files[:limit], start=1):
                print(f"{i}. {title or '(no title)'} | {abs_fp}")
        if orphans:
            print(f"--- Orphans (up to {limit}) ---")
            for i, p in enumerate(orphans[:limit], start=1):
                print(f"{i}. {p}")
        if duplicate_file_paths:
            print(f"--- Duplicate file_path references (up to {limit}) ---")
            for i, (fp, url_title_list) in enumerate(list(duplicate_file_paths.items())[:limit], start=1):
                print(f"{i}. {fp} <- {len(url_title_list)} urls")
                for url, title in url_title_list[:5]:
                    print(f"    - {title or '(no title)'} | {url}")
        if downloaded_rows_no_file_path_count:
            print(f"--- downloaded rows missing file_path (up to {limit}) ---")
            for i, (url, title, _) in enumerate(downloaded_rows_no_file_path[:limit], start=1):
                print(f"{i}. {title or '(no title)'} | {url}")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())


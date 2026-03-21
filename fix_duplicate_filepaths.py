"""
Mark duplicate downloaded file paths as failed so they can be re-downloaded.

For each duplicate file_path in videos where status='downloaded', we keep the
oldest row as 'downloaded' and mark the rest as:
  failed: duplicate file_path

Usage:
  .\\.venv\\Scripts\\python.exe fix_duplicate_filepaths.py
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import config


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _abs_path(project_root: Path, p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def main() -> int:
    project_root = Path(__file__).resolve().parent
    db_path = Path(config.DB_PATH)
    if not db_path.is_absolute():
        db_path = project_root / db_path

    conn = sqlite3.connect(str(db_path))
    try:
        # Group by resolved absolute path (DB file_path strings may differ but point to same file).
        rows = conn.execute(
            """
            SELECT url, title, downloaded_at, file_path
            FROM videos
            WHERE status='downloaded' AND file_path IS NOT NULL
            """
        ).fetchall()
        if not rows:
            print("No downloaded rows with file_path found.")
            return 0

        file_groups: dict[Path, list[tuple[str, str, str]]] = {}
        for url, title, downloaded_at, file_path in rows:
            if not file_path:
                continue
            try:
                abs_fp = _abs_path(project_root, file_path)
            except Exception:
                continue
            file_groups.setdefault(abs_fp, []).append((url, title or "", downloaded_at or ""))

        dup_groups = {fp: v for fp, v in file_groups.items() if len(v) > 1}
        if not dup_groups:
            print("No duplicate physical files (by resolved absolute path) found.")
            return 0

        total_marked = 0
        print(f"Found {len(dup_groups)} duplicate physical file(s) on disk.")

        for abs_fp, url_title_downloaded_list in dup_groups.items():
            # Keep most recent downloaded_at
            sorted_rows = sorted(url_title_downloaded_list, key=lambda x: x[2], reverse=True)
            keep_url = sorted_rows[0][0]
            to_mark = [x[0] for x in sorted_rows[1:]]

            print(f"- {abs_fp}: keeping {keep_url}, marking {len(to_mark)} as failed")
            for url in to_mark:
                conn.execute(
                    """
                    UPDATE videos
                    SET status=?
                    WHERE url=?
                    """,
                    (f"failed: duplicate file_path ({_utc_now_iso()})", url),
                )
                total_marked += 1

        conn.commit()
        print(f"Marked {total_marked} URL(s) for re-download.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())


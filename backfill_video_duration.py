"""Set videos.duration_seconds from local files via ffprobe (one-time backfill).

Requires ffprobe on PATH. Run from repo root:

  python backfill_video_duration.py
  python web/summary_page.py
  # copy web/data.js -> web2/public/data.js
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import db


def _abs_file(project_root: Path, file_path: str | None) -> Path | None:
    if not file_path:
        return None
    p = Path(file_path)
    if p.is_file():
        return p.resolve()
    alt = (project_root / file_path).resolve()
    return alt if alt.is_file() else None


def main() -> int:
    project_root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=str(project_root / "playlist_archive.db"))
    p.add_argument("--dry-run", action="store_true", help="Print counts only")
    args = p.parse_args()
    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT url, file_path, duration_seconds
            FROM videos
            WHERE status = 'downloaded' AND file_path IS NOT NULL
            """
        )
        rows = cur.fetchall()
        updated = 0
        skipped_has_dur = 0
        missing_file = 0
        ffprobe_failed = 0
        for row in rows:
            if row["duration_seconds"] is not None:
                skipped_has_dur += 1
                continue
            abs_p = _abs_file(project_root, row["file_path"])
            if not abs_p:
                missing_file += 1
                continue
            if args.dry_run:
                updated += 1
                continue
            if db.set_video_duration_from_file(conn, row["url"], str(abs_p)):
                updated += 1
            else:
                ffprobe_failed += 1
    finally:
        conn.close()

    print(
        f"duration backfill: updated={updated} "
        f"(skipped already set={skipped_has_dur}, file missing={missing_file}, "
        f"ffprobe failed={ffprobe_failed}, rows scanned={len(rows)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

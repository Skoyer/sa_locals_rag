"""Optional: register video files on disk that are not yet in the DB (orphan URLs)."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import db
from transcription.audio import VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


def _resolve_stored_path(project_root: Path, p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def _norm_key(project_root: Path, resolved: Path) -> str:
    return resolved.relative_to(project_root.resolve()).as_posix()


def sync_orphan_downloads(
    conn: sqlite3.Connection,
    project_root: Path,
    output_dir: Path,
) -> int:
    """
    Insert minimal ``videos`` rows for media files under ``output_dir`` whose resolved
    path is not already represented by any ``videos.file_path``.

    URLs are ``orphan:<relative/posix/path>`` so they do not collide with real video URLs.
    """
    if not output_dir.is_dir():
        logger.warning("OUTPUT_DIR is not a directory: %s", output_dir)
        return 0

    known: set[str] = set()
    for (fp,) in conn.execute("SELECT file_path FROM videos WHERE file_path IS NOT NULL"):
        try:
            known.add(_norm_key(project_root, _resolve_stored_path(project_root, fp)))
        except (ValueError, OSError):
            continue

    added = 0
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        try:
            resolved = path.resolve()
            key = _norm_key(project_root, resolved)
        except ValueError:
            continue

        if key in known:
            continue

        url = "orphan:" + key
        if conn.execute("SELECT 1 FROM videos WHERE url = ?", (url,)).fetchone():
            continue

        stored_path = "./" + key.lstrip("/") if not key.startswith("./") else key
        db.insert_video(
            conn,
            url,
            title=path.stem,
            description="",
            status="downloaded",
            file_path=stored_path,
        )
        db.set_video_duration_from_file(conn, url, stored_path)
        known.add(key)
        added += 1
        logger.info("Registered orphan file as %s (%s)", url, stored_path)

    return added

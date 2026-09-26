"""Resolve ``videos.file_path`` values to real files on this machine.

DB rows often store Windows absolute paths (e.g. ``C:\\...\\downloads\\foo.mp4``)
from the machine that ran the downloader. On another checkout — or after moving
``OUTPUT_DIR`` — the absolute path may be gone while the same basename still
exists under the configured download directory. Resolution order:

1. Absolute path as stored (works when browsing on the original Windows box).
2. Path relative to the project root.
3. Basename under ``OUTPUT_DIR`` (cross-machine / remapped C: drive fallback).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import config

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".m4v", ".mov", ".avi"}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def downloads_dir() -> Path:
    p = Path(config.OUTPUT_DIR)
    if not p.is_absolute():
        p = project_root() / p
    return p.resolve()


def db_path() -> Path:
    p = Path(config.DB_PATH)
    if not p.is_absolute():
        p = project_root() / p
    return p.resolve()


def normalize_stored_path(raw: str) -> str:
    """Normalize separators; keep drive letters intact."""
    return raw.strip().replace("\\", "/")


def resolve_media_path(stored: str | None, *, root: Path | None = None) -> Path | None:
    """Return an existing video Path for a DB ``file_path``, or None."""
    if not stored or not str(stored).strip():
        return None
    root = root or project_root()
    raw = normalize_stored_path(stored)
    candidates: list[Path] = []

    p = Path(stored)
    # Path("C:/foo") is absolute on Windows; on Linux Path("C:/foo") is relative
    # with a drive-like first part — try both the as-stored and posix forms.
    if p.is_absolute():
        candidates.append(p)
    candidates.append(Path(raw))
    if not Path(raw).is_absolute():
        candidates.append((root / raw).resolve())
        # Strip leading ./ 
        stripped = raw.lstrip("./")
        if stripped and stripped != raw:
            candidates.append((root / stripped).resolve())

    basename = Path(raw).name
    if basename:
        candidates.append(downloads_dir() / basename)
        # Also try recursive match under downloads (one level deep is enough)
        dl = downloads_dir()
        if dl.is_dir():
            for hit in dl.rglob(basename):
                if hit.is_file():
                    candidates.append(hit)
                    break

    seen: set[str] = set()
    for c in candidates:
        try:
            key = str(c)
        except Exception:
            continue
        if key in seen:
            continue
        seen.add(key)
        try:
            if c.is_file() and c.suffix.lower() in VIDEO_EXTENSIONS:
                return c.resolve()
        except OSError:
            continue
    return None


def lookup_by_transcript_id(transcript_id: int) -> dict | None:
    """Return title, url, file_path, and resolved path for a transcript id."""
    path = db_path()
    if not path.is_file():
        return None
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT t.id AS transcript_id, v.url, v.title, v.file_path, v.status
            FROM transcripts t
            INNER JOIN videos v ON v.url = t.video_url
            WHERE t.id = ?
            """,
            (transcript_id,),
        ).fetchone()
        if row is None:
            return None
        stored = row["file_path"]
        resolved = resolve_media_path(stored)
        return {
            "transcript_id": int(row["transcript_id"]),
            "url": row["url"] or "",
            "title": row["title"] or "",
            "file_path": stored,
            "status": row["status"] or "",
            "resolved_path": str(resolved) if resolved else None,
            "available": resolved is not None,
        }
    finally:
        conn.close()


def file_available(stored: str | None) -> bool:
    return resolve_media_path(stored) is not None

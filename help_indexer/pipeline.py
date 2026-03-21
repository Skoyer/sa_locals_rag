"""End-to-end: discover → upsert video → Whisper → replace segments (FTS via triggers)."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from help_indexer import discover, media_meta, transcribe_whisper

logger = logging.getLogger(__name__)


def upsert_video(
    conn: sqlite3.Connection,
    *,
    external_id: str,
    title: str,
    description: str,
    filename: str,
    duration_sec: int | None,
) -> int:
    conn.execute(
        """
        INSERT INTO videos (external_id, title, description, filename, duration_sec)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(external_id) DO UPDATE SET
          title = excluded.title,
          description = excluded.description,
          filename = excluded.filename,
          duration_sec = excluded.duration_sec
        """,
        (external_id, title, description, filename, duration_sec),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM videos WHERE external_id = ?",
        (external_id,),
    ).fetchone()
    assert row is not None
    return int(row[0])


def replace_transcript_segments(
    conn: sqlite3.Connection,
    video_id: int,
    segments: list[tuple[float, float, str]],
) -> None:
    conn.execute("DELETE FROM transcript_segments WHERE video_id = ?", (video_id,))
    for start_sec, end_sec, text in segments:
        conn.execute(
            """
            INSERT INTO transcript_segments (video_id, start_sec, end_sec, text)
            VALUES (?, ?, ?, ?)
            """,
            (video_id, start_sec, end_sec, text),
        )
    conn.commit()


def index_one_file(
    conn: sqlite3.Connection,
    external_id: str,
    path: Path,
    *,
    model_name: str,
) -> bool:
    """Transcribe one media file and store segments. Returns True on success."""
    title = path.stem.replace("_", " ").strip() or external_id
    description = ""
    filename = path.name
    duration_sec = media_meta.ffprobe_duration_seconds(path)

    try:
        _full_text, raw = transcribe_whisper.transcribe_with_segments(path, model_name)
        segments = transcribe_whisper.as_db_segments(raw)
        if not segments:
            logger.warning("No segments for %s (empty transcript?)", path)
    except Exception:
        logger.exception("Whisper failed for %s", path)
        return False

    video_id = upsert_video(
        conn,
        external_id=external_id,
        title=title,
        description=description,
        filename=filename,
        duration_sec=duration_sec,
    )
    replace_transcript_segments(conn, video_id, segments)
    logger.info("Indexed %s (%d segments)", external_id, len(segments))
    return True


def run_pipeline(
    conn: sqlite3.Connection,
    media_root: Path,
    *,
    model_name: str,
    limit: int | None = None,
) -> tuple[int, int]:
    """
    Process all discovered files under media_root.

    Returns (success_count, failure_count).
    """
    items = discover.discover_media(media_root)
    ok = 0
    fail = 0
    for i, (external_id, path) in enumerate(items):
        if limit is not None and i >= limit:
            break
        if index_one_file(conn, external_id, path, model_name=model_name):
            ok += 1
        else:
            fail += 1
    return ok, fail

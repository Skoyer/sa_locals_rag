"""Expand FTS hits into fuller transcript passages for RAG prompts."""
from __future__ import annotations

import sqlite3


def _overlap_query(
    conn: sqlite3.Connection,
    video_id: int,
    lo: float,
    hi: float,
) -> str:
    """All segment texts overlapping [lo, hi] in time (same video)."""
    cur = conn.execute(
        """
        SELECT text FROM transcript_segments
        WHERE video_id = ?
          AND start_sec < ?
          AND end_sec > ?
        ORDER BY start_sec
        """,
        (video_id, hi, lo),
    )
    parts = [str(row[0]).strip() for row in cur.fetchall() if row[0]]
    return "\n\n".join(parts)


def expand_transcript_around(
    conn: sqlite3.Connection,
    video_id: int,
    start_sec: float,
    end_sec: float,
    *,
    window_sec: float = 60.0,
) -> str:
    """
    Concatenate all segment texts that overlap the time window
    ``[start_sec - window, end_sec + window]`` for this video.

    If the first pass returns very little text (Whisper micro-segments), retries once
    with **double** the window so the LLM gets enough surrounding lines.
    """
    lo = max(0.0, float(start_sec) - float(window_sec))
    hi = float(max(end_sec, start_sec + 0.05)) + float(window_sec)

    text = _overlap_query(conn, video_id, lo, hi)
    if len(text.strip()) < 120 and window_sec < 240:
        lo2 = max(0.0, float(start_sec) - float(window_sec) * 2)
        hi2 = float(max(end_sec, start_sec + 0.05)) + float(window_sec) * 2
        text2 = _overlap_query(conn, video_id, lo2, hi2)
        if len(text2.strip()) > len(text.strip()):
            text = text2
    return text


def truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"

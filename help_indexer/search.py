"""Full-text search over transcript_segments_fts (for web apps / CLI)."""
from __future__ import annotations

import sqlite3
from typing import Any, Literal

MatchMode = Literal["loose", "strict", "raw"]


def prepare_fts5_match(query: str, *, mode: MatchMode = "loose") -> str | None:
    """
    Build an FTS5 MATCH string.

    - **loose** (default): multi-word queries become OR of prefix terms (``word*``),
      so ``brain washing`` matches segments containing the token ``brainwashing``
      (via ``brain*``) as well as separate ``brain`` / ``washing`` tokens.
      Single-word queries use a trailing ``*`` when length >= 3 (prefix match).
    - **strict**: escape double-quotes only; FTS5 treats space-separated tokens as
      **AND** (default), which often misses compound words in the transcript.
    - **raw**: pass through (only strip); for power users who know FTS5 syntax.
    """
    q = query.strip()
    if not q:
        return None

    if mode == "raw":
        return q

    if mode == "strict":
        return q.replace('"', '""')

    # loose
    if q.startswith('"') and q.endswith('"') and len(q) >= 2:
        inner = q[1:-1].replace('"', '""')
        return f'"{inner}"'

    words = q.split()
    if not words:
        return None

    parts: list[str] = []
    for w in words:
        w = w.replace('"', '""')
        if not w:
            continue
        if w.endswith("*"):
            parts.append(w)
        elif len(w) < 3:
            parts.append(w)
        else:
            parts.append(f"{w}*")

    if len(parts) == 1:
        return parts[0]
    return " OR ".join(parts)


def search_segments(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    match_mode: MatchMode = "loose",
) -> list[dict[str, Any]]:
    """
    Run FTS5 search with BM25 ranking and snippets.

    Returns list of dicts: video_id, video_title, segment_id, start_sec, end_sec,
    snippet_html, score (bm25 — lower is better).
    """
    match = prepare_fts5_match(query, mode=match_mode)
    if match is None:
        return []

    sql = """
    SELECT
      v.id AS video_id,
      v.title AS video_title,
      ts.id AS segment_id,
      ts.start_sec,
      ts.end_sec,
      snippet(transcript_segments_fts, 0, '<b>', '</b>', '...', 32) AS snippet_html,
      bm25(transcript_segments_fts) AS score
    FROM transcript_segments_fts
    JOIN transcript_segments ts ON ts.id = transcript_segments_fts.rowid
    JOIN videos v ON v.id = ts.video_id
    WHERE transcript_segments_fts MATCH ?
    ORDER BY score
    LIMIT ?
    """
    cur = conn.execute(sql, (match, limit))
    rows = cur.fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "video_id": r["video_id"],
                "title": r["video_title"],
                "segment_id": r["segment_id"],
                "start_sec": r["start_sec"],
                "end_sec": r["end_sec"],
                "snippet_html": r["snippet_html"],
                "score": r["score"],
            }
        )
    return out

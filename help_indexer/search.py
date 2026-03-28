"""Full-text search over transcript_segments_fts (for web apps / CLI)."""
from __future__ import annotations

import logging
import re
import sqlite3
import unicodedata
from typing import Any, Literal

logger = logging.getLogger(__name__)

MatchMode = Literal["loose", "strict", "raw"]
LooseJoin = Literal["AND", "OR"]

# In loose mode, drop these so "Tell me about persuasion" becomes persuasion* (not me OR ...).
_LOOSE_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "to",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "me",
        "my",
        "we",
        "us",
        "our",
        "it",
        "its",
        "in",
        "on",
        "at",
        "as",
        "and",
        "or",
        "but",
        "if",
        "of",
        "for",
        "with",
        "by",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "they",
        "them",
        "your",
        "what",
        "which",
        "who",
        "whom",
        "how",
        "why",
        "when",
        "where",
        "can",
        "could",
        "would",
        "should",
        "do",
        "does",
        "did",
        "tell",
        "ask",
        "give",
        "get",
        "got",
        "go",
        "come",
        "about",
        "into",
        "from",
        "just",
        "like",
        "so",
        "no",
        "not",
        "yes",
        "any",
        "some",
        "all",
        "there",
        "here",
        "will",
        "have",
        "has",
        "had",
    }
)


def _clean_token(s: str) -> str:
    """
    Strip leading/trailing punctuation/whitespace from a token.

    FTS5 treats characters like '.' as syntax; a word such as ``persuasion.``
    must not become ``persuasion.*`` in loose mode (syntax error near '.').
    """
    s = s.strip()
    while s and unicodedata.category(s[0])[0] in ("P", "S", "Z"):
        s = s[1:]
    while s and unicodedata.category(s[-1])[0] in ("P", "S", "Z"):
        s = s[:-1]
    return s


def prepare_fts5_match(
    query: str,
    *,
    mode: MatchMode = "loose",
    loose_join: LooseJoin = "AND",
) -> str | None:
    """
    Build an FTS5 MATCH string.

    - **loose**: multi-word queries use **AND** by default (``persuasion* AND ethics*``)
      so results must contain every keyword in the **same segment**—better for
      multi-topic queries. If that returns no rows, :func:`search_segments` retries
      with **OR** (broader recall, e.g. compound tokens). Single-word: prefix ``*``.
    - **strict**: escape double-quotes; tokens are cleaned and space-joined (implicit AND).
    - **raw**: pass through (only strip outer whitespace); can error on bad FTS5 syntax.

    ``loose_join`` only applies when ``mode == \"loose\"`` and there are 2+ terms.
    """
    q = query.strip()
    if not q:
        return None

    if mode == "raw":
        return q

    if mode == "strict":
        words = [_clean_token(w) for w in q.split()]
        words = [w.replace('"', '""') for w in words if w]
        if not words:
            return None
        return " ".join(words)

    # loose
    if q.startswith('"') and q.endswith('"') and len(q) >= 2:
        inner = _clean_token(q[1:-1])
        if not inner:
            return None
        inner = inner.replace('"', '""')
        return f'"{inner}"'

    words = [_clean_token(w) for w in q.split()]
    words = [w for w in words if w]
    if not words:
        return None

    filtered = [w for w in words if w.lower() not in _LOOSE_STOPWORDS]
    if filtered:
        words = filtered

    parts: list[str] = []
    for w in words:
        w = w.replace('"', '""')
        if w.endswith("*"):
            parts.append(w)
        elif len(w) < 3:
            parts.append(w)
        else:
            parts.append(f"{w}*")

    if len(parts) == 1:
        return parts[0]
    sep = " OR " if loose_join == "OR" else " AND "
    return sep.join(parts)


def keyword_search_query_for_rag(question: str, *, max_terms: int = 8) -> str | None:
    """
    Turn a natural-language question into a short keyword string for FTS.

    Use this from RAG clients instead of passing the full sentence to ``/search``,
    which can produce noisy OR matches or empty results.
    """
    if not question.strip():
        return None
    words = re.findall(r"[A-Za-z0-9']+", question)
    cleaned: list[str] = []
    for w in words:
        w = _clean_token(w)
        if not w or len(w) < 2:
            continue
        cleaned.append(w)
    if not cleaned:
        return None
    filtered = [w for w in cleaned if w.lower() not in _LOOSE_STOPWORDS]
    if filtered:
        cleaned = filtered
    return " ".join(cleaned[:max_terms])


def _strict_tokens_for_title_match(query: str) -> list[str]:
    """Tokens from a query for ``title LIKE`` matching (lowercased)."""
    m = prepare_fts5_match(query, mode="strict")
    if not m:
        return []
    return [t.lower() for t in m.split() if len(t) >= 2]


def _fetch_segments_title_all_keywords(
    conn: sqlite3.Connection,
    words: list[str],
    *,
    exclude_segment_ids: set[int],
    limit: int,
) -> list[sqlite3.Row]:
    """
    Segments from videos whose **title** contains every keyword (e.g. ethics stack video).

    Used when FTS AND/OR does not surface a segment that still matches the topic in the title.
    """
    if len(words) < 2 or limit <= 0:
        return []
    conds = " AND ".join(["lower(v.title) LIKE ?" for _ in words])
    params: list[Any] = [f"%{w}%" for w in words]
    q = f"""
    SELECT
      v.id AS video_id,
      v.title AS video_title,
      v.filename AS filename,
      v.external_id AS external_id,
      ts.id AS segment_id,
      ts.start_sec,
      ts.end_sec,
      substr(ts.text, 1, 400) AS snippet_html,
      -0.5 AS score
    FROM transcript_segments ts
    JOIN videos v ON v.id = ts.video_id
    WHERE {conds}
    """
    if exclude_segment_ids:
        ph = ",".join("?" * len(exclude_segment_ids))
        q += f" AND ts.id NOT IN ({ph})"
        params.extend(sorted(exclude_segment_ids))
    q += " ORDER BY v.title, ts.start_sec LIMIT ?"
    params.append(limit)
    cur = conn.execute(q, params)
    return cur.fetchall()


def search_segments(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    match_mode: MatchMode = "loose",
) -> list[dict[str, Any]]:
    """
    Run FTS5 search with BM25 ranking and snippets.

    Returns list of dicts: video_id, title, filename, external_id, segment_id,
    start_sec, end_sec, snippet_html, score (bm25 — lower is better).
    """
    sql = """
    SELECT
      v.id AS video_id,
      v.title AS video_title,
      v.filename AS filename,
      v.external_id AS external_id,
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

    rows: list[sqlite3.Row] = []
    if match_mode == "loose":
        match_and = prepare_fts5_match(query, mode="loose", loose_join="AND")
        if match_and:
            try:
                cur = conn.execute(sql, (match_and, limit))
                rows = cur.fetchall()
            except sqlite3.OperationalError as e:
                err = str(e).lower()
                if "fts5" in err:
                    logger.warning("FTS5 AND query failed for match=%r: %s", match_and, e)
                else:
                    raise
        if not rows:
            match_or = prepare_fts5_match(query, mode="loose", loose_join="OR")
            if match_or and match_or != match_and:
                try:
                    cur = conn.execute(sql, (match_or, limit))
                    rows = cur.fetchall()
                except sqlite3.OperationalError as e:
                    err = str(e).lower()
                    if "fts5" in err:
                        logger.warning("FTS5 OR query failed for match=%r: %s", match_or, e)
                    else:
                        raise
    else:
        match = prepare_fts5_match(query, mode=match_mode)
        if match is None:
            return []
        try:
            cur = conn.execute(sql, (match, limit))
            rows = cur.fetchall()
        except sqlite3.OperationalError as e:
            err = str(e).lower()
            if "fts5" in err:
                logger.warning("FTS5 query failed for match=%r mode=%s: %s", match, match_mode, e)
                return []
            raise

    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for r in rows:
        sid = int(r["segment_id"])
        seen.add(sid)
        out.append(
            {
                "video_id": r["video_id"],
                "title": r["video_title"],
                "filename": r["filename"],
                "external_id": r["external_id"],
                "segment_id": sid,
                "start_sec": r["start_sec"],
                "end_sec": r["end_sec"],
                "snippet_html": r["snippet_html"],
                "score": r["score"],
            }
        )

    # Title-based supplement: videos whose title contains every keyword (stack / ethics in title).
    if match_mode == "loose" and len(out) < limit:
        title_words = _strict_tokens_for_title_match(query)
        if len(title_words) >= 2:
            extra_rows = _fetch_segments_title_all_keywords(
                conn,
                title_words,
                exclude_segment_ids=seen,
                limit=limit - len(out),
            )
            for r in extra_rows:
                out.append(
                    {
                        "video_id": r["video_id"],
                        "title": r["video_title"],
                        "filename": r["filename"],
                        "external_id": r["external_id"],
                        "segment_id": int(r["segment_id"]),
                        "start_sec": r["start_sec"],
                        "end_sec": r["end_sec"],
                        "snippet_html": r["snippet_html"],
                        "score": r["score"],
                    }
                )

    return out

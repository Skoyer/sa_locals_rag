"""
Build structured chat messages for the RAG query loop.
Converts retrieved transcript segments + user question into
a grounded, citation-enforcing LLM prompt.
"""
from __future__ import annotations

from typing import Iterable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_seconds(sec: float) -> str:
    """Convert float seconds to MM:SS or H:MM:SS string."""
    sec = int(sec or 0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _clean_snippet(html: str) -> str:
    """Strip <b>/<b> tags from FTS5 snippet_html."""
    return html.replace("<b>", "**").replace("</b>", "**")


# ---------------------------------------------------------------------------
# Hit selection / deduplication
# ---------------------------------------------------------------------------

def select_hits(
    hits: list[dict],
    *,
    max_hits: int = 8,
    dedupe_window_sec: int = 60,
) -> list[dict]:
    """
    Choose up to max_hits segments for the prompt.

    Deduplication: skips any hit from the same video whose
    start time falls within dedupe_window_sec of an already-chosen hit.
    This prevents the prompt being flooded by many adjacent segments
    from the same video on the same topic.
    """
    chosen: list[dict] = []
    seen: dict[int, list[float]] = {}  # video_id -> list of chosen start_sec

    for hit in hits:
        vid = hit.get("video_id")
        start = float(hit.get("start_sec") or 0)

        if vid in seen:
            if any(abs(start - prev) < dedupe_window_sec for prev in seen[vid]):
                continue

        seen.setdefault(vid, []).append(start)
        chosen.append(hit)

        if len(chosen) >= max_hits:
            break

    return chosen


# ---------------------------------------------------------------------------
# Core prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a transcript-grounded assistant. Your only job is to answer the \
user's question using the provided transcript excerpts from Scott Adams' \
videos.

Rules:
1. Answer exclusively from the provided sources. Do NOT use outside knowledge \
   or generic definitions.
2. Cite the source number (e.g. [Source 3]) for every factual claim you make.
3. If two sources appear to contradict each other, note the conflict explicitly.
4. If the evidence is too thin or off-topic, say:
   "I don't have enough evidence in the retrieved transcripts to answer this \
   confidently."
5. Use Scott Adams' specific language and framing where possible — \
   prefer quoting or paraphrasing the transcript over abstract interpretation.
6. Be concise. Avoid padding or filler sentences.\
"""

ANSWER_FORMAT = """\
Answer using this exact format:

**Answer:**
- [2–6 bullet points, each with at least one citation like [Source N]]

**Evidence strength:** Strong | Moderate | Weak

**Gaps:**
- [What is missing or unclear from the retrieved excerpts. \
   If nothing is missing, say "None."]
"""


def build_messages(question: str, hits: Iterable[dict]) -> list[dict]:
    """
    Build a two-message chat payload (system + user) ready to send to any
    OpenAI-compatible chat endpoint.

    Parameters
    ----------
    question : str
        The raw user question.
    hits : iterable of dicts
        Search results from help_indexer /search — each dict must contain:
        title, start_sec, end_sec, snippet_html, score.

    Returns
    -------
    list of {"role": ..., "content": ...} dicts.
    """
    hits = list(hits)

    if not hits:
        context_text = "[No transcript segments were retrieved. " \
                       "The question may use terms not present in the archive.]"
    else:
        blocks = []
        for i, hit in enumerate(hits, start=1):
            title   = hit.get("title") or "Untitled"
            start   = float(hit.get("start_sec") or 0)
            end     = float(hit.get("end_sec") or 0)
            snippet = _clean_snippet(hit.get("snippet_html") or "")
            score   = hit.get("score")

            blocks.append(
                f"[Source {i}]\n"
                f"Video : {title}\n"
                f"Time  : {_fmt_seconds(start)} → {_fmt_seconds(end)}\n"
                f"Score : {score:.3f}\n"
                f"Excerpt: {snippet}"
            )
        context_text = "\n\n".join(blocks)

    user_content = (
        f"**Question:** {question}\n\n"
        f"---\n\n"
        f"**Retrieved transcript sources ({len(hits)} segments):**\n\n"
        f"{context_text}\n\n"
        f"---\n\n"
        f"{ANSWER_FORMAT}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Quick debug / preview
# ---------------------------------------------------------------------------

def preview(question: str, hits: list[dict]) -> None:
    """Print the full prompt payload to stdout. Useful for debugging."""
    messages = build_messages(question, hits)
    for msg in messages:
        print(f"\n{'='*60}")
        print(f"ROLE: {msg['role'].upper()}")
        print('='*60)
        print(msg["content"])

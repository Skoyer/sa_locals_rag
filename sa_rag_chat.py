#!/usr/bin/env python3
"""
sa_rag_chat.py — RAG chat UI for sa_locals_rag
Requires: pip install gradio requests openai

Usage:
  1. Start help_indexer API:   python -m help_indexer.cli serve
  2. Start LM Studio server:   Enable "Local Server" in LM Studio (port 1234)
  3. Run this app:             python sa_rag_chat.py
  4. Open browser:             http://localhost:7860
"""

from __future__ import annotations

import html
import logging
import os
import re
import sqlite3
import textwrap
from pathlib import Path

import gradio as gr
import requests
from openai import OpenAI

import config  # playlist_archive.db path (same .env as downloader)
from help_indexer.expand import expand_transcript_around, truncate_text
from help_indexer import config as hi_config
from help_indexer.search import keyword_search_query_for_rag

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
INDEXER_URL = os.environ.get("HELP_INDEXER_URL", "http://localhost:8000")
LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://localhost:1234")
# Locals feed URLs look like: https://locals.com/scottadams/feed?post=5751847
LOCALS_CREATOR_SLUG = os.environ.get("LOCALS_CREATOR_SLUG", "scottadams")

# Model options matching what is loaded in LM Studio.
# Change values to the exact model identifiers shown in LM Studio's server tab.
MODELS = {
    "Qwen2.5 Coder 7B (fast, 4.36 GB)":        "qwen2.5-coder-7b-instruct",
    "DeepSeek Coder v2 Lite (balanced, 8.88 GB)": "deepseek-coder-v2-lite-instruct",
    "GLM 4.7 Flash (largest, 16.89 GB)":        "glm-4-flash",
}

DEFAULT_SEARCH_LIMIT = 6  # how many transcript segments to retrieve
DEFAULT_CONTEXT_WINDOW_SEC = float(os.environ.get("RAG_CONTEXT_WINDOW_SEC", "120"))
DEFAULT_MAX_CONTEXT_CHARS = int(os.environ.get("RAG_MAX_CONTEXT_CHARS_PER_HIT", "6000"))
DISPLAY_SNIPPET_CHARS = 2000  # how much expanded text to show in the UI panel

# Cache: (title_lower, filename_lower) -> real Locals URL or None
_playlist_url_cache: dict[tuple[str, str | None], str | None] = {}


def _playlist_db_path() -> Path:
    p = Path(os.environ.get("PLAYLIST_DB_PATH", config.DB_PATH))
    if not p.is_absolute():
        p = Path(__file__).resolve().parent / p
    return p.resolve()


def _help_videos_db_path() -> Path:
    """Same DB as ``help_indexer`` (transcript_segments)."""
    p = Path(os.environ.get("HELP_VIDEOS_DB", hi_config.DB_PATH))
    if not p.is_absolute():
        p = Path(__file__).resolve().parent / p
    return p.resolve()


def _safe_video_id(v: object) -> int | None:
    """API/JSON may send int, float, or str; ``help_indexer`` uses INTEGER video_id."""
    if v is None:
        return None
    try:
        i = int(float(v))
    except (TypeError, ValueError):
        return None
    return i if i >= 0 else None


# ── Helpers ────────────────────────────────────────────────────────────────────

def search_segments(query: str, limit: int = DEFAULT_SEARCH_LIMIT, mode: str = "loose") -> list[dict]:
    """Call the help_indexer /search endpoint and return hits."""
    try:
        r = requests.get(
            f"{INDEXER_URL.rstrip('/')}/search",
            params={"q": query, "limit": limit, "mode": mode},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return [{"error": f"Unexpected response type: {type(data).__name__}"}]
        return data
    except Exception as e:
        return [{"error": str(e)}]


def strip_html(text: str) -> str:
    """Remove HTML tags (e.g. <b>...</b> from snippet_html)."""
    return re.sub(r"<[^>]+>", "", text)


def seconds_to_ts(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS timestamp string."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def append_timestamp_to_url(url: str, start_sec: float) -> str:
    """Append &t=seconds (Locals often uses this on feed?post=… URLs)."""
    t = int(max(0, start_sec))
    if not url or not url.startswith("http"):
        return url
    if re.search(r"([&?#])(?:t|start|time)=", url, re.I):
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={t}"


def extract_post_id_from_filename(name: str | None) -> str | None:
    """yt-dlp / downloader often saves ``… [post=5924409].mp4`` — use for real feed links."""
    if not name:
        return None
    m = re.search(r"\[post=(\d+)\]", name, re.I)
    return m.group(1) if m else None


def feed_url_for_post_id(post_id: str) -> str:
    return f"https://locals.com/{LOCALS_CREATOR_SLUG}/feed?post={post_id}"


def lookup_playlist_post_url(title: str, filename: str | None) -> str | None:
    """
    Resolve a Locals **feed** URL for this video.

    1) ``[post=ID]`` in the indexed filename (matches downloader naming) → canonical feed URL.
    2) Exact title match in playlist_archive.db.
    3) Basename match on file_path (Windows paths normalized).
    """
    dbp = _playlist_db_path()
    base = Path(filename).name if filename else ""
    key = (title.strip().lower(), base.lower() or None)
    if key in _playlist_url_cache:
        return _playlist_url_cache[key]

    post_id = extract_post_id_from_filename(base) or extract_post_id_from_filename(title)
    if post_id:
        u = feed_url_for_post_id(post_id)
        if dbp.is_file():
            try:
                conn = sqlite3.connect(str(dbp))
                cur = conn.cursor()
                row = cur.execute(
                    "SELECT url FROM videos WHERE status = 'downloaded' AND url LIKE ? LIMIT 1",
                    (f"%post={post_id}%",),
                ).fetchone()
                conn.close()
                if row and str(row[0]).startswith("http"):
                    u = str(row[0])
            except (OSError, sqlite3.Error):
                pass
        _playlist_url_cache[key] = u
        return u

    if not dbp.is_file():
        _playlist_url_cache[key] = None
        return None

    base_l = base.lower()
    try:
        conn = sqlite3.connect(str(dbp))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        row = cur.execute(
            "SELECT url FROM videos WHERE status = 'downloaded' AND title = ? LIMIT 1",
            (title,),
        ).fetchone()
        if row:
            u = str(row["url"])
            _playlist_url_cache[key] = u
            conn.close()
            return u

        if base_l:
            row = cur.execute(
                """
                SELECT url FROM videos
                WHERE status = 'downloaded' AND file_path IS NOT NULL
                  AND (
                    lower(replace(file_path, '\\', '/')) LIKE '%' || ? || '%'
                    OR lower(file_path) LIKE '%' || ? || '%'
                  )
                LIMIT 1
                """,
                (base_l, base_l),
            ).fetchone()
            if row:
                u = str(row["url"])
                _playlist_url_cache[key] = u
                conn.close()
                return u

        conn.close()
    except (OSError, sqlite3.Error):
        pass

    _playlist_url_cache[key] = None
    return None


def build_locals_url(title: str, start_sec: float, filename: str | None = None) -> str:
    """
    Prefer feed URL from ``[post=ID]`` / playlist DB; last resort: guessed slug (usually wrong).
    """
    real = lookup_playlist_post_url(title, filename)
    if real:
        return append_timestamp_to_url(real, start_sec)
    # No post id: open creator feed (cannot deep-link a specific post without DB / filename id).
    return append_timestamp_to_url(
        f"https://locals.com/{LOCALS_CREATOR_SLUG}/feed",
        start_sec,
    )


def build_context_block(
    hits: list[dict],
    *,
    search_query_used: str,
    expand_conn: sqlite3.Connection | None = None,
    context_window_sec: float = DEFAULT_CONTEXT_WINDOW_SEC,
    max_context_chars_per_hit: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> tuple[str, str]:
    """
    Returns (llm_context_text, html_for_sources_panel).

    When ``expand_conn`` is set (read-only ``help_videos.db``), each hit is expanded to
    the full overlapping transcript in a ±window around the FTS match — much more text
    for the LLM than the short FTS snippet alone.
    """
    if not hits:
        return "", (
            "<p><strong>No search results.</strong> Check that <code>help_indexer</code> is running "
            "and <code>help_videos.db</code> has transcripts.</p>"
        )

    first = hits[0]
    if isinstance(first, dict) and first.get("error") is not None:
        err = html.escape(str(first.get("error", "Unknown error")))
        return "", f"<p>⚠️ Search error: <code>{err}</code></p>"

    llm_parts: list[str] = []
    li_items: list[str] = []
    total_llm_chars = 0

    for i, hit in enumerate(hits, 1):
        if not isinstance(hit, dict):
            continue
        title = hit.get("title") or "Unknown"
        filename = hit.get("filename")
        if isinstance(filename, str):
            filename = filename or None
        else:
            filename = None
        start_sec = float(hit.get("start_sec", 0))
        end_sec = float(hit.get("end_sec", 0))
        snippet = strip_html(str(hit.get("snippet_html", "")))
        score = float(hit.get("score", 0))
        url = build_locals_url(title, start_sec, filename)
        ts_start = seconds_to_ts(start_sec)
        ts_end = seconds_to_ts(end_sec)

        vid = _safe_video_id(hit.get("video_id"))
        expanded = ""
        if expand_conn is not None and vid is not None:
            try:
                expanded = expand_transcript_around(
                    expand_conn,
                    vid,
                    start_sec,
                    end_sec,
                    window_sec=context_window_sec,
                )
            except (sqlite3.Error, TypeError, ValueError):
                expanded = ""

        if expanded.strip():
            llm_body = truncate_text(expanded.strip(), max_context_chars_per_hit)
        else:
            llm_body = snippet

        total_llm_chars += len(llm_body)

        llm_parts.append(
            f'[Context {i}] Video: "{title}" | Time: {ts_start}–{ts_end}\n{llm_body}'
        )

        safe_title = html.escape(title)
        esc_url = html.escape(url, quote=True)
        display_body = expanded.strip() if expanded.strip() else snippet
        display_body = truncate_text(display_body, DISPLAY_SNIPPET_CHARS)
        safe_display = html.escape(display_body)
        src_lbl = "Expanded passage" if expanded.strip() else "FTS snippet (expand DB missing or empty)"
        li_items.append(
            "<li style='margin-bottom:1em;'>"
            f"<p><strong>{i}. <a href=\"{esc_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{safe_title}</a></strong> "
            f"— <code>{html.escape(ts_start)}</code> → <code>{html.escape(ts_end)}</code> "
            f"<small>(score: {score:.3f}) · {html.escape(src_lbl)}</small></p>"
            f"<blockquote style='margin:0.4em 0;border-left:3px solid #ccc;padding-left:0.8em;'>{safe_display}</blockquote>"
            "</li>"
        )

    if expand_conn is not None and _help_videos_db_path().is_file():
        expand_note = (
            f"<p><small>Passages expanded ±{context_window_sec:.0f}s from "
            f"<code>help_videos.db</code> (max {max_context_chars_per_hit} chars per block for the LLM). "
            f"<strong>~{total_llm_chars} characters</strong> of context text sent to the LLM.</small></p>"
        )
    else:
        expand_note = (
            "<p><small><strong>No local DB expansion:</strong> put <code>help_videos.db</code> next to this app "
            f"(or set <code>HELP_VIDEOS_DB</code>) to send fuller transcript text to the LLM. "
            f"Right now the LLM only sees FTS snippets (~{total_llm_chars} chars total).</small></p>"
        )

    parts: list[str] = [
        "<h4>🔍 Retrieved segments</h4>",
        f"<p><small>Indexer query: <code>{html.escape(search_query_used)}</code></small></p>",
        expand_note,
        "<ul style='padding-left:1.2em;'>",
        *li_items,
        "</ul>",
        "<p><small>Links use <code>feed?post=…</code> from your download filenames when possible. "
        f"Set <code>LOCALS_CREATOR_SLUG</code> if your community is not <code>{html.escape(LOCALS_CREATOR_SLUG)}</code>.</small></p>",
    ]
    return "\n\n".join(llm_parts), "".join(parts)


def ask_lm_studio(
    question: str,
    context: str,
    model_key: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """Send question + retrieved context to LM Studio; return the completion text."""
    model_id = MODELS.get(model_key, list(MODELS.values())[0])
    client   = OpenAI(base_url=f"{LM_STUDIO_URL}/v1", api_key="lm-studio")

    system_prompt = textwrap.dedent("""
        You are a knowledgeable assistant that answers questions strictly using
        the provided transcript excerpts from Scott Adams videos.
        - Always cite which context number(s) you used, e.g. [Context 2].
        - If the context does not contain enough information, say so honestly.
        - If the user only names a topic or keyword (not a full question), synthesize themes and
          concrete points from the excerpts instead of only listing where the word appears.
        - Be concise and direct. Use bullet points when listing multiple ideas.
        - Do NOT make up information not present in the context.
    """).strip()

    user_message = f"""Question: {question}

--- Transcript Context ---
{context}
--- End Context ---

Please answer the question using only the context above."""

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return response.choices[0].message.content or "(No response)"
    except Exception as e:
        return (
            f"❌ LM Studio error: {e}\n\n"
            "Make sure:\n"
            "1. LM Studio server is running (see LM_STUDIO_URL)\n"
            "2. A model is loaded\n"
            "3. The model ID in MODELS matches the server tab"
        )


# ── Use-case demo functions ────────────────────────────────────────────────────

USE_CASES = {
    "💡 Core Concept":     "What is the most important principle of persuasion?",
    "🧠 Mindset":          "How does Scott Adams talk about thinking clearly?",
    "🗣️ Communication":   "What advice does he give about how to talk to people?",
    "📈 Success":          "What does Scott Adams say about achieving goals?",
    "🤖 AI & Future":      "What are his thoughts on artificial intelligence?",
    "🧩 Systems vs Goals": "What is the difference between systems and goals?",
}


# ── Gradio UI ──────────────────────────────────────────────────────────────────

def run_rag(
    question: str,
    model_key: str,
    search_limit: int,
    search_mode: str,
    temperature: float,
    context_window_sec: float,
    max_context_chars_per_hit: float,
) -> tuple[str, str]:
    """Main pipeline: retrieve → augment → generate."""
    if not question.strip():
        return "Please enter a question.", ""

    # Full sentences are bad FTS queries; use keyword compaction for /search.
    search_q = keyword_search_query_for_rag(question) or question.strip()
    hits = search_segments(search_q, limit=search_limit, mode=search_mode)

    dbp = _help_videos_db_path()
    conn: sqlite3.Connection | None = None
    if dbp.is_file():
        try:
            uri = dbp.resolve().as_uri() + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
        except sqlite3.Error as e:
            logger.warning("Could not open help_videos.db read-only at %s: %s", dbp, e)
            conn = None

    try:
        context, segments_html = build_context_block(
            hits,
            search_query_used=search_q,
            expand_conn=conn,
            context_window_sec=float(context_window_sec),
            max_context_chars_per_hit=int(max_context_chars_per_hit),
        )
    finally:
        if conn is not None:
            conn.close()

    if not context:
        return "", segments_html

    answer = ask_lm_studio(question, context, model_key, temperature)
    return answer, segments_html


def load_use_case(label: str) -> str:
    return USE_CASES.get(label, "")


with gr.Blocks(
    title="Scott Adams RAG Chat",
    theme=gr.themes.Soft(),
    css=".answer-box textarea { font-size: 15px !important; line-height: 1.6 !important; }",
) as demo:

    gr.Markdown("# 🎙️ Scott Adams — RAG Chat")
    gr.Markdown(
        "Ask any question. The app sends **keywords** derived from your question to the local "
        "search API (see *Indexer query* under sources), retrieves transcript snippets, then asks your LLM. "
        "Video links open Locals in a **new tab** when the file name contains `[post=…]` from the downloader."
    )

    with gr.Row():
        with gr.Column(scale=2):
            question_box = gr.Textbox(
                label="Your Question",
                placeholder="e.g. What does Scott Adams say about persuasion?",
                lines=2,
            )

            gr.Markdown(
                "**Quick Use Cases** — pick a preset, then click **Load** to paste it into the box above "
                "(you can edit before **Ask**)."
            )
            with gr.Row():
                use_case_dd = gr.Dropdown(
                    choices=list(USE_CASES.keys()),
                    label="Preset",
                    value=None,
                    interactive=True,
                )
                load_btn = gr.Button("Load", scale=0)

            load_btn.click(load_use_case, inputs=use_case_dd, outputs=question_box)

            with gr.Accordion("⚙️ Settings", open=False):
                model_dd = gr.Dropdown(
                    choices=list(MODELS.keys()),
                    value=list(MODELS.keys())[0],
                    label="LM Studio Model",
                )
                search_limit_sl = gr.Slider(
                    minimum=1, maximum=20, value=DEFAULT_SEARCH_LIMIT, step=1,
                    label="Segments to Retrieve (more = richer context, slower)",
                )
                search_mode_rd = gr.Radio(
                    choices=["loose", "strict", "raw"],
                    value="loose",
                    label="Search Mode",
                    info="loose: multi-word AND + title boost; strict: AND tokens; raw: FTS syntax",
                )
                ctx_window_sl = gr.Slider(
                    minimum=15.0,
                    maximum=300.0,
                    value=DEFAULT_CONTEXT_WINDOW_SEC,
                    step=5.0,
                    label="Transcript window (± seconds around each hit)",
                    info="Pulls full segments from help_videos.db around the match for the LLM.",
                )
                max_ctx_sl = gr.Slider(
                    minimum=800.0,
                    maximum=12000.0,
                    value=float(DEFAULT_MAX_CONTEXT_CHARS),
                    step=200.0,
                    label="Max characters per context block (LLM)",
                )
                temp_sl = gr.Slider(
                    minimum=0.0, maximum=1.0, value=0.3, step=0.05,
                    label="Temperature (0=focused, 1=creative)",
                )

            ask_btn = gr.Button("🚀 Ask", variant="primary", size="lg")

        with gr.Column(scale=3):
            answer_box = gr.Textbox(
                label="💬 LLM Answer",
                lines=12,
                interactive=False,
                elem_classes=["answer-box"],
            )
            segments_box = gr.HTML(
                label="📄 Source segments",
                value="<p><em>Run a search to see retrieved chunks here.</em></p>",
            )

    ask_btn.click(
        run_rag,
        inputs=[
            question_box,
            model_dd,
            search_limit_sl,
            search_mode_rd,
            temp_sl,
            ctx_window_sl,
            max_ctx_sl,
        ],
        outputs=[answer_box, segments_box],
    )
    question_box.submit(
        run_rag,
        inputs=[
            question_box,
            model_dd,
            search_limit_sl,
            search_mode_rd,
            temp_sl,
            ctx_window_sl,
            max_ctx_sl,
        ],
        outputs=[answer_box, segments_box],
    )

    gr.Markdown(
        "---\n"
        f"**Prerequisites:** `python -m help_indexer.cli serve` → `{INDEXER_URL}`. "
        f"**help_videos.db** (set `HELP_VIDEOS_DB`) must exist beside this app for **expanded transcript** context. "
        f"**Playlist DB** for links: `playlist_archive.db` or `PLAYLIST_DB_PATH`. "
        f"**LM Studio:** `{LM_STUDIO_URL}`."
    )


if __name__ == "__main__":
    demo.launch(inbrowser=True)

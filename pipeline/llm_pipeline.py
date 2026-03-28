"""Two-pass LM Studio pipeline: transcript → structured JSON on `videos`."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

import db

logger = logging.getLogger(__name__)

DEFAULT_LM_BASE = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
DEFAULT_MODEL = os.getenv("LM_STUDIO_MODEL", "local-model")

# LM Studio often uses n_ctx=4096; few-shot + system + 3× long transcripts can overflow.
# Tune with LLM_MAX_TRANSCRIPT_CHARS / LLM_BATCH_SIZE if you still see 400 context errors.
def _max_transcript_chars() -> int:
    return max(400, int(os.getenv("LLM_MAX_TRANSCRIPT_CHARS", "2500")))


def _llm_batch_size() -> int:
    return max(1, min(8, int(os.getenv("LLM_BATCH_SIZE", "3"))))


def _truncate_transcript(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = max_chars - 40
    return text[:cut].rstrip() + "\n… [truncated for LLM context; raise LLM_MAX_TRANSCRIPT_CHARS or load a larger n_ctx model]"


def _batch_with_truncated_transcripts(
    batch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cap = _max_transcript_chars()
    out: list[dict[str, Any]] = []
    for row in batch:
        t = row["transcript"]
        if len(t) > cap:
            logger.info(
                "Truncating transcript id=%s from %s to ~%s chars for LM context",
                row.get("transcript_id"),
                len(t),
                cap,
            )
        out.append({**row, "transcript": _truncate_transcript(t, cap)})
    return out

_LOGS_DIR = Path("logs")
_FAILED_IDS = _LOGS_DIR / "failed_ids.txt"
_FAILURE_LOG = _LOGS_DIR / "llm_failures.log"

# Refreshed at each run_llm_pipeline() start; prevents duplicate lines in failed_ids.txt
_failed_ids_logged: set[int] | None = None

# Few-shot examples (short) — embedded at top of every prompt
_FEW_SHOT = """
Example A — transcript:
"Always start with agreement before you persuade. People lower their guard when you align first."

Example A — JSON:
{"core_lesson": "Lead with agreement to reduce resistance before persuading.", "key_concepts": ["agreement", "persuasion", "resistance"], "complexity_indicators": ["assumes basic rapport"]}

Example B — transcript:
"The phrase 'compared to what' reframes any claim into a comparison game you control."

Example B — JSON:
{"core_lesson": "Use 'compared to what' to reframe claims into favorable comparisons.", "key_concepts": ["compared to what", "reframing", "comparison"], "complexity_indicators": ["builds on basic framing"]}
"""

def _pass1_system(n: int) -> str:
    keys = ", ".join(f"VIDEO_{i + 1}" for i in range(n))
    return f"""You are an expert analyst of Scott Adams' persuasion micro-lessons.
For each labeled transcript below, output ONE JSON object whose keys are {keys} (use only the labels present). Each value must be an object with exactly these fields (never use {{}} unless the transcript block is literally empty or unreadable noise):
{{
  "core_lesson": "1-sentence takeaway",
  "key_concepts": ["4-8 noun phrases using exact wording from the transcript"],
  "complexity_indicators": ["e.g. requires prior knowledge of X", "builds on basic persuasion"]
}}
If there is any usable English in the transcript, you must fill core_lesson and key_concepts—do not return {{}} out of caution. No prose outside the JSON."""


def _pass2_system(n: int) -> str:
    keys = ", ".join(f"VIDEO_{i + 1}" for i in range(n))
    return f"""You are an expert analyst of Scott Adams' persuasion micro-lessons.
Using the summary and key_concepts from Pass 1 for each video, output ONE JSON object with keys {keys} (only labels present). Each value must be a full object with these fields (never use {{}} when Pass 1 provided a core_lesson):
{{
  "primary_topics": ["1-3 items"],
  "secondary_topics": ["..."],
  "persuasion_techniques": ["..."],
  "psychology_concepts": ["..."],
  "difficulty": "beginner" | "intermediate" | "advanced",
  "prerequisites": ["concepts this lesson assumes the viewer knows"],
  "builds_toward": ["concepts this lesson unlocks"],
  "related_lessons_keywords": ["exact phrases for FTS5 matching"],
  "tone": ["..."],
  "use_cases": ["..."],
  "is_persuasion_focused": true | false
}}
No prose outside the JSON."""


def load_transcript_text(path: str, project_root: Path | None = None) -> str:
    """Load transcript text from JSON on disk.

    Supports:
    - Project wrapper: ``whisper_result.text`` / ``whisper_result.segments``
    - Raw Whisper: top-level ``text`` or ``segments`` with ``text`` fields
    """
    root = project_root or Path.cwd()
    p = Path(path)
    if not p.is_absolute():
        p = (root / path.lstrip("./")).resolve()
    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)

    wr = data.get("whisper_result")
    if isinstance(wr, dict):
        t = (wr.get("text") or "").strip()
        if t:
            return t
        return _join_segments(wr.get("segments"))

    t = (data.get("text") or "").strip()
    if t:
        return t
    return _join_segments(data.get("segments"))


def _join_segments(segments: Any) -> str:
    if not isinstance(segments, list):
        return ""
    parts: list[str] = []
    for seg in segments:
        if isinstance(seg, dict) and seg.get("text"):
            parts.append(str(seg["text"]).strip())
        elif isinstance(seg, str):
            parts.append(seg.strip())
    return " ".join(parts).strip()


def _lm_client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("LM_STUDIO_BASE_URL", DEFAULT_LM_BASE),
        api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
    )


_RAW_DEBUG = _LOGS_DIR / "llm_raw_samples.log"


def _iter_json_dicts(text: str) -> list[dict[str, Any]]:
    """Parse every top-level JSON object in ``text`` (handles multiple blobs + prose between).

    Greedy ``{...}`` regex breaks when the model emits two JSON objects with non-JSON text
    between them (common with instruction echo). ``JSONDecoder.raw_decode`` only consumes
    one value per call, so we walk the string and collect dicts.
    """
    dec = json.JSONDecoder()
    out: list[dict[str, Any]] = []
    i = 0
    n = len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i >= n or text[i] != "{":
            i += 1
            continue
        try:
            val, end = dec.raw_decode(text, i)
            if isinstance(val, dict):
                out.append(val)
            i = end
        except json.JSONDecodeError:
            i += 1
    return out


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    objs = _iter_json_dicts(text)
    if not objs:
        raise ValueError("no JSON object in response")
    if len(objs) == 1:
        return objs[0]
    merged: dict[str, Any] = {}
    for o in objs:
        for k, v in o.items():
            if k.startswith("VIDEO_") or k.lower().startswith("video_"):
                merged[k] = v
    if merged:
        return merged
    # Multiple flat JSON objects (e.g. wrong line + echo + final); last is usually correct.
    return objs[-1]


def _video_slot(obj: dict[str, Any], index: int) -> dict[str, Any] | None:
    """Get VIDEO_n with common key variants."""
    for key in (
        f"VIDEO_{index + 1}",
        f"video_{index + 1}",
        f"Video_{index + 1}",
    ):
        v = obj.get(key)
        if isinstance(v, dict):
            return v
    return None


def _maybe_log_raw(pass_label: str, raw: str, ids: list[int]) -> None:
    if os.getenv("LLM_DEBUG_RAW_RESPONSE", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        return
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_RAW_DEBUG, "a", encoding="utf-8") as f:
        f.write(f"\n--- {pass_label} transcript_ids={ids} ---\n")
        f.write((raw or "")[:16000])
        f.write("\n")


def _parse_pass1_batch(raw: str, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        obj = _extract_json_object(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Pass1 JSON parse error: %s", e)
        return [{} for _ in batch]
    out: list[dict[str, Any]] = []
    n = len(batch)
    for i in range(n):
        part = _video_slot(obj, i)
        if part is None and n == 1 and isinstance(obj, dict):
            if "core_lesson" in obj or "key_concepts" in obj:
                part = obj
        if not isinstance(part, dict):
            out.append({})
            continue
        if part == {}:
            out.append({})
            continue
        out.append(part)
    while len(out) < n:
        out.append({})
    return out[:n]


def _parse_pass2_batch(raw: str, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        obj = _extract_json_object(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Pass2 JSON parse error: %s", e)
        return [{} for _ in batch]
    out: list[dict[str, Any]] = []
    n = len(batch)
    for i in range(n):
        part = _video_slot(obj, i)
        if part is None and n == 1 and isinstance(obj, dict):
            if "primary_topics" in obj or "difficulty" in obj:
                part = obj
        if not isinstance(part, dict):
            out.append({})
            continue
        if part == {}:
            out.append({})
            continue
        out.append(part)
    while len(out) < n:
        out.append({})
    return out[:n]


def _chat(system: str, user: str) -> str:
    client = _lm_client()
    model = os.getenv("LM_STUDIO_MODEL", DEFAULT_MODEL)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
    )
    choice = resp.choices[0].message
    return (choice.content or "").strip()


def _append_failed(transcript_id: int) -> None:
    """Append ``transcript_id`` once per process lifetime (and skip if already on disk)."""
    global _failed_ids_logged
    if _failed_ids_logged is None:
        _failed_ids_logged = _read_retry_ids()
    if transcript_id in _failed_ids_logged:
        return
    _failed_ids_logged.add(transcript_id)
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_FAILED_IDS, "a", encoding="utf-8") as f:
        f.write(f"{transcript_id}\n")


def _log_failure_detail(
    transcript_id: int,
    title: str,
    pass_num: int,
    reason: str,
) -> None:
    """Append one line to ``logs/llm_failures.log`` (TSV: time, id, pass, reason, title)."""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = (title or "").replace("\t", " ").replace("\n", " ")[:300]
    line = (
        f"{datetime.now(timezone.utc).isoformat()}\t"
        f"{transcript_id}\tpass{pass_num}\t{reason}\t{safe_title}\n"
    )
    with open(_FAILURE_LOG, "a", encoding="utf-8") as f:
        f.write(line)


def _log_run_diagnostics(
    conn: sqlite3.Connection,
    *,
    queued: int,
    only_missing: bool,
) -> None:
    """Explain counts: 260 videos vs 194 queued, etc."""
    total_downloaded = conn.execute(
        "SELECT COUNT(*) FROM videos WHERE status = 'downloaded'"
    ).fetchone()[0]
    with_transcript = conn.execute(
        """
        SELECT COUNT(*) FROM transcripts t
        INNER JOIN videos v ON v.url = t.video_url
        WHERE v.status = 'downloaded'
        """
    ).fetchone()[0]
    missing_core = conn.execute(
        """
        SELECT COUNT(*) FROM transcripts t
        INNER JOIN videos v ON v.url = t.video_url
        WHERE v.status = 'downloaded'
          AND (v.core_lesson IS NULL OR TRIM(COALESCE(v.core_lesson, '')) = '')
        """
    ).fetchone()[0]
    logger.info(
        "DB: %d downloaded videos, %d with transcript rows, %d missing core_lesson (enrichment).",
        total_downloaded,
        with_transcript,
        missing_core,
    )
    logger.info(
        "This run: %d video(s) queued. Progress bar uses this count (not transcript id). "
        "Transcript id=t.id (AUTOINCREMENT); last id can be 260 while only 194 run if you use "
        "--only-missing, --limit, or gaps in t.id.",
        queued,
    )


def dedupe_failed_ids_file() -> int:
    """Rewrite ``logs/failed_ids.txt`` with unique sorted ids. Returns count of unique ids."""
    ids = sorted(_read_retry_ids())
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _FAILED_IDS.write_text(
        "".join(f"{i}\n" for i in ids),
        encoding="utf-8",
    )
    global _failed_ids_logged
    _failed_ids_logged = set(ids)
    return len(ids)


def _read_retry_ids() -> set[int]:
    if not _FAILED_IDS.is_file():
        return set()
    out: set[int] = set()
    for line in _FAILED_IDS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.add(int(line))
        except ValueError:
            continue
    return out


def _labeled_batch_user(
    batch: list[dict[str, Any]],
    *,
    pass1: bool,
    pass1_payloads: list[dict[str, Any]] | None = None,
) -> str:
    lines: list[str] = [_FEW_SHOT.strip(), ""]
    for i, row in enumerate(batch):
        lab = f"VIDEO_{i + 1}"
        if pass1:
            lines.append(f"[{lab}]")
            lines.append(row["transcript"])
            lines.append("")
        else:
            p1 = (pass1_payloads or [{}])[i] if pass1_payloads else {}
            core = p1.get("core_lesson") or ""
            kc = p1.get("key_concepts") or []
            lines.append(f"[{lab}] Pass 1 summary:")
            lines.append(f"core_lesson: {core}")
            lines.append(f"key_concepts: {json.dumps(kc, ensure_ascii=False)}")
            lines.append("")
    lines.append("Output only the single JSON object as specified.")
    return "\n".join(lines)


def _empty_pass1() -> dict[str, Any]:
    return {
        "core_lesson": None,
        "key_concepts": None,
        "complexity_indicators": None,
    }


def _empty_pass2() -> dict[str, Any]:
    return {
        "primary_topics": None,
        "secondary_topics": None,
        "persuasion_techniques": None,
        "psychology_concepts": None,
        "difficulty": None,
        "prerequisites": None,
        "builds_toward": None,
        "related_lessons_keywords": None,
        "tone": None,
        "use_cases": None,
        "is_persuasion_focused": None,
    }


def _apply_pass1_to_db(
    conn: sqlite3.Connection,
    url: str,
    data: dict[str, Any],
) -> None:
    core = data.get("core_lesson")
    summary = core if isinstance(core, str) and core.strip() else None
    def j(x: Any) -> str | None:
        if x is None:
            return None
        if isinstance(x, (list, dict)):
            return json.dumps(x, ensure_ascii=False)
        return json.dumps(x, ensure_ascii=False)

    conn.execute(
        """
        UPDATE videos SET
          summary_text = ?,
          core_lesson = ?,
          key_concepts = ?,
          complexity_indicators = ?
        WHERE url = ?
        """,
        (
            summary,
            core if isinstance(core, str) else None,
            j(data.get("key_concepts")),
            j(data.get("complexity_indicators")),
            url,
        ),
    )
    conn.commit()


def _apply_pass2_to_db(conn: sqlite3.Connection, url: str, data: dict[str, Any]) -> None:
    def j(x: Any) -> str | None:
        if x is None:
            return None
        return json.dumps(x, ensure_ascii=False)

    ip = data.get("is_persuasion_focused")
    ip_int: int | None
    if ip is True:
        ip_int = 1
    elif ip is False:
        ip_int = 0
    else:
        ip_int = None

    conn.execute(
        """
        UPDATE videos SET
          primary_topics = ?,
          secondary_topics = ?,
          persuasion_techniques = ?,
          psychology_concepts = ?,
          difficulty = ?,
          prerequisites = ?,
          builds_toward = ?,
          related_lessons_keywords = ?,
          tone = ?,
          use_cases = ?,
          is_persuasion_focused = ?
        WHERE url = ?
        """,
        (
            j(data.get("primary_topics")),
            j(data.get("secondary_topics")),
            j(data.get("persuasion_techniques")),
            j(data.get("psychology_concepts")),
            data.get("difficulty") if isinstance(data.get("difficulty"), str) else None,
            j(data.get("prerequisites")),
            j(data.get("builds_toward")),
            j(data.get("related_lessons_keywords")),
            j(data.get("tone")),
            j(data.get("use_cases")),
            ip_int,
            url,
        ),
    )
    conn.commit()


def fetch_rows(
    conn: sqlite3.Connection,
    *,
    limit: int | None,
    retry_only: set[int] | None,
    project_root: Path,
    offset: int = 0,
    only_missing: bool = False,
) -> list[dict[str, Any]]:
    """Eligible rows: downloaded, transcript loads, optional retry filter.

    ``offset`` skips the first N *eligible* rows (after transcript load), then ``limit`` applies.
    ``only_missing`` restricts to rows with no ``core_lesson`` yet (incremental runs).
    """
    missing_sql = ""
    if only_missing and retry_only is None:
        missing_sql = (
            " AND (v.core_lesson IS NULL OR TRIM(COALESCE(v.core_lesson, '')) = '')"
        )
    q = f"""
        SELECT t.id, t.video_url, t.transcript_path, v.title
        FROM transcripts t
        INNER JOIN videos v ON v.url = t.video_url
        WHERE v.status = 'downloaded'{missing_sql}
        ORDER BY t.id
    """
    cur = conn.execute(q)
    rows: list[dict[str, Any]] = []
    skipped = 0
    for tid, video_url, tpath, title in cur.fetchall():
        if retry_only is not None and int(tid) not in retry_only:
            continue
        try:
            text = load_transcript_text(tpath, project_root)
        except OSError as e:
            logger.warning("Missing transcript file for id=%s: %s", tid, e)
            _append_failed(int(tid))
            continue
        if not text.strip():
            _append_failed(int(tid))
            continue
        if skipped < offset:
            skipped += 1
            continue
        rows.append(
            {
                "transcript_id": int(tid),
                "url": video_url,
                "transcript_path": tpath,
                "title": title or "",
                "transcript": text,
            }
        )
        if limit is not None and len(rows) >= limit:
            break
    return rows


def run_llm_pipeline(
    db_path: str = "playlist_archive.db",
    *,
    limit: int | None = None,
    offset: int = 0,
    only_missing: bool = False,
    retry_failed: bool = False,
    project_root: Path | None = None,
    pause_event: threading.Event | None = None,
    status_callback: Callable[[int, str, int, str], None] | None = None,
    status: object | None = None,
) -> tuple[int, int]:
    """Returns (success_count, failure_count).

    If ``status`` is a :class:`ui.status_window.StatusWindow`, its ``set_total`` and
    ``update`` are used (and ``pause_event`` is taken from it unless overridden).
    """
    global _failed_ids_logged
    _failed_ids_logged = _read_retry_ids()

    root = project_root or Path.cwd()
    db.init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        retry_ids = _read_retry_ids() if retry_failed else None
        if retry_failed and not retry_ids:
            logger.warning("retry-failed set but %s empty or missing", _FAILED_IDS)
        rows = fetch_rows(
            conn,
            limit=limit,
            retry_only=retry_ids,
            project_root=root,
            offset=offset,
            only_missing=only_missing,
        )
        _log_run_diagnostics(conn, queued=len(rows), only_missing=only_missing)
    finally:
        conn.close()

    if status is not None:
        status.set_total(len(rows))
        status_callback = status.update
        pause_event = status.pause_event

    pause_ev = pause_event or threading.Event()
    ok = 0
    fail = 0
    batch_size = _llm_batch_size()

    conn = sqlite3.connect(db_path)
    try:
        for i in range(0, len(rows), batch_size):
            while pause_ev.is_set():
                time.sleep(0.15)
            batch = rows[i : i + batch_size]
            batch = _batch_with_truncated_transcripts(batch)
            if status is not None:
                status.mark_batch_tick()

            n = len(batch)
            pass1_batch_exc = False
            pass2_batch_exc = False
            # Pass 1
            try:
                u1 = _labeled_batch_user(batch, pass1=True)
                r1 = _chat(_pass1_system(n), u1)
                p1_parsed = _parse_pass1_batch(r1, batch)
                if any(not p.get("core_lesson") for p in p1_parsed):
                    _maybe_log_raw(
                        "pass1",
                        r1,
                        [b["transcript_id"] for b in batch],
                    )
            except Exception as e:
                pass1_batch_exc = True
                logger.exception("Pass 1 batch failed: %s", e)
                err = repr(e)[:400]
                for row in batch:
                    _log_failure_detail(
                        row["transcript_id"],
                        row["title"],
                        1,
                        f"pass1_batch_error: {err}",
                    )
                p1_parsed = [{} for _ in batch]

            try:
                u2 = _labeled_batch_user(
                    batch,
                    pass1=False,
                    pass1_payloads=p1_parsed,
                )
                r2 = _chat(_pass2_system(n), u2)
                p2_parsed = _parse_pass2_batch(r2, batch)
                if any(not p or p == {} for p in p2_parsed):
                    _maybe_log_raw(
                        "pass2",
                        r2,
                        [b["transcript_id"] for b in batch],
                    )
            except Exception as e:
                pass2_batch_exc = True
                logger.exception("Pass 2 batch failed: %s", e)
                err = repr(e)[:400]
                for row in batch:
                    _log_failure_detail(
                        row["transcript_id"],
                        row["title"],
                        2,
                        f"pass2_batch_error: {err}",
                    )
                p2_parsed = [{} for _ in batch]

            for j, row in enumerate(batch):
                tid = row["transcript_id"]
                url = row["url"]
                title = row["title"]
                data1 = p1_parsed[j] if j < len(p1_parsed) else {}
                data2 = p2_parsed[j] if j < len(p2_parsed) else {}

                if not data1 or not data1.get("core_lesson"):
                    try:
                        _apply_pass1_to_db(conn, url, _empty_pass1())
                        _apply_pass2_to_db(conn, url, _empty_pass2())
                    except Exception:
                        logger.exception("DB empty pass1/2 %s", url)
                    if not pass1_batch_exc:
                        _log_failure_detail(
                            tid,
                            title,
                            1,
                            "pass1_no_core_lesson_model_returned_empty_or_bad_json",
                        )
                    _append_failed(tid)
                    fail += 1
                    if status_callback:
                        status_callback(tid, title, 1, "failed")
                    continue

                try:
                    _apply_pass1_to_db(conn, url, data1)
                except Exception:
                    logger.exception("DB pass1 %s", url)
                    _log_failure_detail(tid, title, 1, "pass1_db_write_error")
                    _append_failed(tid)
                    fail += 1
                    if status_callback:
                        status_callback(tid, title, 1, "failed")
                    continue

                if status_callback:
                    status_callback(tid, title, 1, "success")

                if not data2 or data2 == {}:
                    try:
                        _apply_pass2_to_db(conn, url, _empty_pass2())
                    except Exception:
                        logger.exception("DB empty pass2 %s", url)
                    if not pass2_batch_exc:
                        _log_failure_detail(
                            tid,
                            title,
                            2,
                            "pass2_empty_model_returned_empty_or_bad_json",
                        )
                    _append_failed(tid)
                    fail += 1
                    if status_callback:
                        status_callback(tid, title, 2, "failed")
                    continue

                try:
                    _apply_pass2_to_db(conn, url, data2)
                    ok += 1
                    if status_callback:
                        status_callback(tid, title, 2, "success")
                except Exception:
                    logger.exception("DB pass2 %s", url)
                    _log_failure_detail(tid, title, 2, "pass2_db_write_error")
                    _append_failed(tid)
                    fail += 1
                    if status_callback:
                        status_callback(tid, title, 2, "failed")
    finally:
        conn.close()

    return ok, fail


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Two-pass LLM enrichment for videos")
    p.add_argument("--db", default="playlist_archive.db", help="SQLite database path")
    p.add_argument("--limit", type=int, default=None, help="Max videos to process")
    p.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip the first N eligible videos (same order as --limit).",
    )
    p.add_argument(
        "--only-missing",
        action="store_true",
        help="Only videos with no core_lesson yet (recommended for the next batch).",
    )
    p.add_argument("--retry-failed", action="store_true", help="Only IDs listed in logs/failed_ids.txt")
    p.add_argument(
        "--dedupe-failed-log",
        action="store_true",
        help="Rewrite logs/failed_ids.txt with unique sorted ids, then exit",
    )
    p.add_argument("--project-root", type=Path, default=None, help="Root for relative transcript paths")
    args = p.parse_args()
    if args.dedupe_failed_log:
        n = dedupe_failed_ids_file()
        print(f"Deduped failed_ids.txt: {n} unique transcript id(s).")
        return
    root = args.project_root or Path.cwd()
    ok, fail = run_llm_pipeline(
        db_path=args.db,
        limit=args.limit,
        offset=args.offset,
        only_missing=args.only_missing,
        retry_failed=args.retry_failed,
        project_root=root,
    )
    print(f"Done. success_steps={ok} failure_steps={fail}")


if __name__ == "__main__":
    main()

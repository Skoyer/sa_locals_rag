"""DB-driven transcription: candidates, path resolution, JSON + transcripts table."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import db
from transcription import audio, config, whisper_runner

logger = logging.getLogger(__name__)


def _abs_path(project_root: Path, p: str | None) -> Path | None:
    """Resolve stored file_path the same way as check_downloads.py."""
    if not p:
        return None
    path = Path(p)
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def _transcript_rel_path(project_root: Path, json_path: Path) -> str:
    """Store transcript path like ./transcriptions/foo.json (posix, relative to project root)."""
    try:
        rel = json_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return str(json_path.resolve())
    s = rel.as_posix()
    if not s.startswith("."):
        s = "./" + s
    return s


def _as_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        if hasattr(x, "item"):
            return float(x.item())
        return float(x)
    except (TypeError, ValueError):
        return None


def _whisper_result_for_json(result: dict[str, Any]) -> dict[str, Any]:
    """Keep text + segments; drop heavy / non-JSON-friendly keys if present."""
    out: dict[str, Any] = {"text": result.get("text", "")}
    segs = result.get("segments")
    if segs is not None:
        safe_segments = []
        for seg in segs:
            if not isinstance(seg, dict):
                continue
            safe_segments.append(
                {
                    "id": seg.get("id"),
                    "seek": seg.get("seek"),
                    "start": _as_float(seg.get("start")),
                    "end": _as_float(seg.get("end")),
                    "text": seg.get("text", ""),
                }
            )
        out["segments"] = safe_segments
    return out


def iter_candidates(conn: sqlite3.Connection) -> Iterator[dict[str, Any]]:
    """Rows eligible for transcription."""
    cur = conn.execute(
        """
        SELECT url, title, file_path
        FROM videos
        WHERE status = 'downloaded' AND transcribed = 0 AND file_path IS NOT NULL
        ORDER BY url
        """
    )
    for url, title, file_path in cur.fetchall():
        yield {"url": url, "title": title or "", "file_path": file_path}


def process_one(
    conn: sqlite3.Connection,
    row: dict[str, Any],
    *,
    project_root: Path,
    transcript_dir: Path,
    model_name: str,
) -> bool:
    """Transcribe one video row. Returns True on success."""
    video_path = _abs_path(project_root, row["file_path"])
    if not video_path or not video_path.is_file():
        logger.warning("Skipping missing file for %s: %s", row["url"], row["file_path"])
        return False

    stem = video_path.stem
    audio_dir = transcript_dir / "audio"
    wav_path = audio_dir / f"{stem}.wav"
    json_path = transcript_dir / f"{stem}.json"

    try:
        audio.extract_audio(video_path, wav_path)
        whisper_result = whisper_runner.transcribe_audio(str(wav_path), model_name)
        payload = {
            "video_url": row["url"],
            "title": row["title"],
            "file_path": row["file_path"],
            "model": model_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "whisper_result": _whisper_result_for_json(whisper_result),
        }
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        transcript_path_str = _transcript_rel_path(project_root, json_path)
        db.insert_transcript(
            conn,
            video_url=row["url"],
            transcript_path=transcript_path_str,
            model_name=model_name,
            created_at=payload["created_at"],
        )
        db.mark_video_transcribed(conn, row["url"])
        logger.info("Transcribed %s -> %s", row["url"], transcript_path_str)
        return True
    except Exception:
        logger.exception("Transcription failed for %s", row["url"])
        return False
    finally:
        if wav_path.is_file():
            try:
                wav_path.unlink()
            except OSError as e:
                logger.debug("Could not remove temp wav %s: %s", wav_path, e)


def process(
    conn: sqlite3.Connection,
    *,
    model_name: str | None = None,
    limit: int | None = None,
) -> tuple[int, int]:
    """
    Process transcription candidates. Returns (success_count, failure_or_skip_count).
    """
    root = config.project_root()
    tdir = Path(config.TRANSCRIPT_DIR)
    if not tdir.is_absolute():
        tdir = (root / tdir).resolve()
    model = model_name or config.WHISPER_MODEL

    ok = 0
    bad = 0
    n = 0
    for row in iter_candidates(conn):
        if limit is not None and n >= limit:
            break
        n += 1
        if process_one(conn, row, project_root=root, transcript_dir=tdir, model_name=model):
            ok += 1
        else:
            bad += 1
    return ok, bad

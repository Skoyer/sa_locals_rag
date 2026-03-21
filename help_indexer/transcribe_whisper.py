"""Whisper transcription with timestamped segments."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_model = None
_model_name: str | None = None


def get_model(model_name: str) -> Any:
    global _model, _model_name
    import whisper  # noqa: PLC0415

    if _model is not None and _model_name == model_name:
        return _model
    logger.info("Loading Whisper model %r…", model_name)
    _model = whisper.load_model(model_name)
    _model_name = model_name
    return _model


def transcribe_with_segments(
    media_path: Path,
    model_name: str,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Run Whisper on a video or audio file.

    Returns (full_text, segments) where each segment has start, end, text (from Whisper).
    """
    model = get_model(model_name)
    result = model.transcribe(str(media_path), verbose=False)
    text = (result.get("text") or "").strip()
    raw = result.get("segments") or []
    return text, raw


def as_db_segments(raw_segments: list[dict[str, Any]]) -> list[tuple[float, float, str]]:
    """Convert Whisper segments to (start_sec, end_sec, text) for DB insert."""
    from help_indexer.textutil import normalize_segment_text  # noqa: PLC0415

    out: list[tuple[float, float, str]] = []
    for seg in raw_segments:
        if not isinstance(seg, dict):
            continue
        t = normalize_segment_text(str(seg.get("text", "")))
        if not t:
            continue
        start = _as_float(seg.get("start"))
        end = _as_float(seg.get("end"))
        if start is None or end is None:
            continue
        out.append((start, end, t))
    return out


def _as_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        if hasattr(x, "item"):
            return float(x.item())
        return float(x)
    except (TypeError, ValueError):
        return None

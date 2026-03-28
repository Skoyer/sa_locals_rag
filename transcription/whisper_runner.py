"""Lazy-loaded Whisper model and transcription."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_model = None
_model_name: str | None = None


def get_model(model_name: str) -> Any:
    """Load and cache a Whisper model by name (e.g. tiny, base, small, medium, large)."""
    global _model, _model_name
    import whisper  # noqa: PLC0415 — heavy import; load only when transcribing

    if _model is not None and _model_name == model_name:
        return _model
    logger.info("Loading Whisper model %r (first run may download weights)...", model_name)
    _model = whisper.load_model(model_name)
    _model_name = model_name
    return _model


def transcribe_audio(audio_path: str, model_name: str) -> dict[str, Any]:
    """Run Whisper on a WAV (or other supported) file; return full result dict."""
    model = get_model(model_name)
    return model.transcribe(audio_path)

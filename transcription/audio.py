"""Extract mono 16 kHz WAV for Whisper via FFmpeg."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".m4v", ".mov", ".avi"}


def require_ffmpeg() -> str:
    """Return path to ffmpeg or raise RuntimeError."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install FFmpeg and ensure it is available in your shell."
        )
    return ffmpeg


def extract_audio(video_path: Path, wav_out: Path) -> Path:
    """Extract audio to a 16 kHz mono WAV file. Creates parent dirs."""
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    ffmpeg = require_ffmpeg()
    wav_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(wav_out),
    ]
    logger.debug("Running: %s", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"ffmpeg failed (exit {proc.returncode}): {err[:2000]}")
    return wav_out

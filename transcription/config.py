"""Transcription settings; reuses downloader config for DB_PATH and OUTPUT_DIR."""
from __future__ import annotations

import os
from pathlib import Path

# Project root config (loads .env)
import config as project_config  # noqa: TID252 — intentional package boundary

OUTPUT_DIR: str = project_config.OUTPUT_DIR
DB_PATH: str = project_config.DB_PATH

TRANSCRIPT_DIR: str = os.environ.get("TRANSCRIPT_DIR", "./transcriptions")
WHISPER_MODEL: str = os.environ.get("WHISPER_MODEL", "small")


def project_root() -> Path:
    """Repository root (parent of the transcription package)."""
    return Path(__file__).resolve().parent.parent

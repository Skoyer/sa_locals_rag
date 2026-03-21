"""Environment-driven paths for the help indexer (separate from playlist downloader)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Directory to scan for video/audio
MEDIA_DIR: str = os.environ.get("HELP_MEDIA_DIR", "./downloads")

# SQLite DB for videos + segments + FTS
DB_PATH: str = os.environ.get("HELP_VIDEOS_DB", "./help_videos.db")

WHISPER_MODEL: str = os.environ.get("HELP_WHISPER_MODEL", "small")


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent

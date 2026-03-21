"""Duration and basic metadata via ffprobe."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def ffprobe_duration_seconds(path: Path) -> int | None:
    """Return duration rounded to whole seconds, or None if unknown."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        logger.warning("ffprobe not on PATH; duration_sec will be NULL")
        return None
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        return int(round(float(proc.stdout.strip())))
    except ValueError:
        return None

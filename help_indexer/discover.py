"""Scan a directory tree for video/audio files."""
from __future__ import annotations

from pathlib import Path

MEDIA_EXTENSIONS = frozenset(
    {
        ".mp4",
        ".mkv",
        ".mov",
        ".m4v",
        ".webm",
        ".avi",
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".ogg",
        ".opus",
    }
)


def discover_media(media_root: Path) -> list[tuple[str, Path]]:
    """
    Return (external_id, absolute_path) for each file under media_root.

    external_id is the path relative to media_root without extension (POSIX),
    so nested files stay unique (e.g. ``course/intro`` for ``course/intro.mp4``).
    """
    root = media_root.resolve()
    if not root.is_dir():
        return []

    out: list[tuple[str, Path]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        rel = p.relative_to(root)
        external_id = rel.with_suffix("").as_posix()
        out.append((external_id, p.resolve()))
    return out

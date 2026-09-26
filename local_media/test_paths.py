"""Lightweight checks for local_media path resolution (no pytest required)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_media.paths import resolve_media_path  # noqa: E402


def main() -> int:
    demo = ROOT / "downloads" / "demo_local_playback.mp4"
    if not demo.is_file():
        print("SKIP: demo mp4 not present")
        return 0

    win = r"C:\Users\Demo\sa_locals_rag\downloads\demo_local_playback.mp4"
    assert resolve_media_path(win) == demo.resolve(), resolve_media_path(win)
    assert resolve_media_path("./downloads/demo_local_playback.mp4") == demo.resolve()
    assert resolve_media_path("missing_file_xyz.mp4") is None
    print("OK local_media path resolution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

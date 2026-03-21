"""Normalize transcript text for storage and search."""
from __future__ import annotations

import re


def normalize_segment_text(text: str) -> str:
    s = (text or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

"""Single-call hierarchical topic tree from sampled summaries."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
from pathlib import Path

from openai import OpenAI

import db

logger = logging.getLogger(__name__)

DATA = Path("data")


def _client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
    )


def _extract_json_array(text: str) -> list:
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        raise ValueError("no JSON array")
    return json.loads(m.group(0))


def sample_evenly(rows: list[sqlite3.Row], k: int = 50) -> list[sqlite3.Row]:
    if len(rows) <= k:
        return rows
    step = len(rows) / k
    out: list[sqlite3.Row] = []
    for i in range(k):
        idx = int(i * step)
        out.append(rows[idx])
    return out


def run_build_topic_tree(db_path: str = "playlist_archive.db") -> None:
    db.init_db(db_path)
    DATA.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT t.id AS tid, v.cluster_id, v.summary_text
        FROM transcripts t
        INNER JOIN videos v ON v.url = t.video_url
        WHERE v.summary_text IS NOT NULL AND TRIM(v.summary_text) != ''
        ORDER BY v.cluster_id, t.id
        """
    )
    rows = list(cur.fetchall())
    conn.close()

    picked = sample_evenly(rows, 50)
    lines = [f"id={r['tid']}: {r['summary_text'][:500]}" for r in picked]
    user = (
        "You have summaries of Scott Adams micro-lessons.\n"
        "Create a hierarchical topic tree (max depth 3) for the best learning progression.\n"
        "Output as JSON array of nodes:\n"
        '[{"topic": "...", "level": 1, "subtopics": ["..."], '
        '"recommended_video_ids": [...], "progression_note": "..."}]\n\n'
        + "\n".join(lines)
    )

    model = os.getenv("LM_STUDIO_MODEL", "local-model")
    client = _client()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You reply with a single JSON array only. video ids are integers.",
                },
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        raw = (resp.choices[0].message.content or "").strip()
        tree = _extract_json_array(raw)
    except Exception as e:
        logger.exception("topic tree failed: %s", e)
        tree = []

    (DATA / "topic_tree.json").write_text(
        json.dumps(tree, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="playlist_archive.db")
    args = p.parse_args()
    run_build_topic_tree(db_path=args.db)


if __name__ == "__main__":
    main()

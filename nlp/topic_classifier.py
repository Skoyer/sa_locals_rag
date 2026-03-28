"""Zero-shot multi-label topic buckets from summary_text."""
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


def _client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
    )


def _log_failed(tid: int) -> None:
    Path("logs").mkdir(parents=True, exist_ok=True)
    with open("logs/failed_ids.txt", "a", encoding="utf-8") as f:
        f.write(f"{tid}\n")


def run_topic_classifier(
    db_path: str = "playlist_archive.db",
    *,
    batch_size: int = 10,
) -> None:
    db.init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT t.id AS tid, v.url, v.summary_text
            FROM videos v
            INNER JOIN transcripts t ON t.video_url = v.url
            WHERE v.summary_text IS NOT NULL AND TRIM(v.summary_text) != ''
            ORDER BY t.id
            """
        )
        rows = list(cur.fetchall())
    finally:
        conn.close()

    model = os.getenv("LM_STUDIO_MODEL", "local-model")
    client = _client()
    conn = sqlite3.connect(db_path)

    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        parts = []
        for r in chunk:
            parts.append(f"[ITEM_{r['tid']}]\nSummary: {r['summary_text']}\n")
        user = "\n".join(parts)
        user += (
            "\nCategories (use any subset; you may add 1–2 new labels if needed): "
            '["persuasion","politics","self-programming","hypnosis","cognitive_bias",'
            '"career","negotiation","humor","systems_thinking","personal_brand",'
            '"media_criticism","identity","decision_making"]\n'
            "Output one JSON object mapping keys ITEM_<transcript_id> to JSON arrays of strings."
        )
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You output only valid JSON: an object whose keys are ITEM_<id> and values are JSON arrays of strings.",
                    },
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            raw = (resp.choices[0].message.content or "").strip()
            obj = json.loads(re.search(r"\{[\s\S]*\}", raw).group(0))
        except Exception as e:
            logger.exception("topic batch failed: %s", e)
            for r in chunk:
                _log_failed(int(r["tid"]))
                conn.execute(
                    "UPDATE videos SET topic_buckets = ? WHERE url = ?",
                    ("[]", r["url"]),
                )
            conn.commit()
            continue

        for r in chunk:
            tid = int(r["tid"])
            key = f"ITEM_{tid}"
            buckets = obj.get(key)
            if not isinstance(buckets, list):
                _log_failed(tid)
                buckets = []
            conn.execute(
                "UPDATE videos SET topic_buckets = ? WHERE url = ?",
                (json.dumps(buckets, ensure_ascii=False), r["url"]),
            )
        conn.commit()

    conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="playlist_archive.db")
    args = p.parse_args()
    run_topic_classifier(db_path=args.db)


if __name__ == "__main__":
    main()

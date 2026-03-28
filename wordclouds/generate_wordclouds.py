"""Per-video, per-cluster, per-topic-bucket, and master word clouds."""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from wordcloud import WordCloud  # noqa: E402

import db

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
PER_VIDEO = ROOT / "per_video"
CLUSTERS = ROOT / "clusters"
TOPICS = ROOT / "topics"


def _join_json_list(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return " ".join(str(x) for x in data)
        return str(data)
    except json.JSONDecodeError:
        return raw


def get_wordcloud_path(transcript_id: int) -> Path:
    """Return path to per-video word cloud PNG for a transcript row id."""
    return PER_VIDEO / f"{transcript_id}.png"


def run_wordclouds(db_path: str = "playlist_archive.db") -> None:
    db.init_db(db_path)
    PER_VIDEO.mkdir(parents=True, exist_ok=True)
    CLUSTERS.mkdir(parents=True, exist_ok=True)
    TOPICS.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT t.id AS tid, v.url, v.title,
               v.key_concepts, v.persuasion_techniques, v.psychology_concepts,
               t.transcript_path, v.topic_buckets, v.cluster_id
        FROM transcripts t
        INNER JOIN videos v ON v.url = t.video_url
        """
    )
    rows = list(cur.fetchall())

    from pipeline.llm_pipeline import load_transcript_text

    project_root = Path.cwd()
    master_parts: list[str] = []
    cluster_text: dict[int, list[str]] = defaultdict(list)
    topic_text: dict[str, list[str]] = defaultdict(list)

    wc_kw = dict(
        background_color="black",
        colormap="plasma",
        width=800,
        height=400,
    )

    for r in rows:
        tid = int(r["tid"])
        path = r["transcript_path"]
        try:
            tr = load_transcript_text(path, project_root)
        except OSError:
            logger.warning("skip missing transcript tid=%s", tid)
            tr = ""
        kc = _join_json_list(r["key_concepts"])
        pt = _join_json_list(r["persuasion_techniques"])
        psy = _join_json_list(r["psychology_concepts"])
        blob = " ".join([tr, kc, pt, psy]).strip()
        if not blob:
            continue

        wc = WordCloud(**wc_kw).generate(blob)
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        out = PER_VIDEO / f"{tid}.png"
        plt.savefig(out, bbox_inches="tight", pad_inches=0, facecolor="black")
        plt.close()

        try:
            rel = out.relative_to(project_root)
        except ValueError:
            rel = out
        conn.execute(
            "UPDATE videos SET wordcloud_path = ? WHERE url = ?",
            (str(rel).replace("\\", "/"), r["url"]),
        )

        master_parts.append(tr + " " + kc)

        cid = r["cluster_id"]
        if cid is not None:
            cluster_text[int(cid)].append(blob)

        tb = r["topic_buckets"]
        if tb:
            try:
                buckets = json.loads(tb)
                if isinstance(buckets, list):
                    for b in buckets:
                        topic_text[str(b)].append(blob)
            except json.JSONDecodeError:
                pass

    conn.commit()
    conn.close()

    if master_parts:
        big = "\n".join(master_parts)
        wc = WordCloud(**wc_kw).generate(big)
        plt.figure(figsize=(12, 6))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        plt.savefig(ROOT / "master_wordcloud.png", bbox_inches="tight", facecolor="black")
        plt.close()

    for cid, texts in cluster_text.items():
        blob = "\n".join(texts)
        if not blob.strip():
            continue
        wc = WordCloud(**wc_kw).generate(blob)
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        plt.savefig(CLUSTERS / f"cluster_{cid}.png", bbox_inches="tight", facecolor="black")
        plt.close()

    for name, texts in topic_text.items():
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:80]
        blob = "\n".join(texts)
        if not blob.strip():
            continue
        wc = WordCloud(**wc_kw).generate(blob)
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        plt.savefig(TOPICS / f"{safe}.png", bbox_inches="tight", facecolor="black")
        plt.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="playlist_archive.db")
    args = p.parse_args()
    run_wordclouds(db_path=args.db)


if __name__ == "__main__":
    main()

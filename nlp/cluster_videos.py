"""Embeddings + KMeans + LLM cluster names."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sqlite3
from pathlib import Path

import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

import db

logger = logging.getLogger(__name__)

DATA = Path("data")


def _client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
    )


def _extract_json(text: str) -> dict:
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("no JSON object")
    return json.loads(m.group(0))


def run_clustering(
    db_path: str = "playlist_archive.db",
    *,
    n_clusters: int | None = None,
) -> None:
    db.init_db(db_path)
    DATA.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT t.id AS tid, v.url, v.title, v.summary_text, v.key_concepts,
               v.primary_topics
        FROM transcripts t
        INNER JOIN videos v ON v.url = t.video_url
        WHERE v.summary_text IS NOT NULL AND TRIM(v.summary_text) != ''
        ORDER BY t.id
        """
    )
    rows = list(cur.fetchall())
    conn.close()

    if not rows:
        logger.warning("No rows to cluster.")
        return

    def join_json_field(raw: str | None) -> str:
        if not raw:
            return ""
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return " ".join(str(x) for x in data)
            return str(data)
        except json.JSONDecodeError:
            return raw

    texts: list[str] = []
    ids_order: list[int] = []
    for r in rows:
        tid = int(r["tid"])
        ids_order.append(tid)
        st = (r["summary_text"] or "").strip()
        kc = join_json_field(r["key_concepts"])
        pt = join_json_field(r["primary_topics"])
        texts.append(f"{st} {kc} {pt}".strip())

    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(texts, show_progress_bar=True)
    arr = np.asarray(emb, dtype=np.float32)
    np.save(DATA / "embeddings.npy", arr)
    (DATA / "embedding_ids.json").write_text(
        json.dumps(ids_order, indent=2), encoding="utf-8"
    )

    k = n_clusters if n_clusters is not None else int(
        os.getenv("CLUSTER_N_CLUSTERS", "15")
    )
    k = max(1, min(k, len(rows)))
    clusterer = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = clusterer.fit_predict(arr)

    conn = sqlite3.connect(db_path)
    clusters_out: list[tuple[int, str, int]] = []
    for r, lab in zip(rows, labels):
        tid = int(r["tid"])
        url = r["url"]
        title = r["title"] or ""
        cid = int(lab)
        conn.execute("UPDATE videos SET cluster_id = ? WHERE url = ?", (cid, url))
        clusters_out.append((tid, title, cid))
    conn.commit()

    with open(DATA / "clusters.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "cluster_id"])
        w.writerows(clusters_out)

    # Name clusters via LLM
    cluster_ids = sorted({c for _, _, c in clusters_out})
    model_lm = os.getenv("LM_STUDIO_MODEL", "local-model")
    client = _client()
    names: dict[str, dict] = {}

    by_cluster: dict[int, list[sqlite3.Row]] = {}
    for r, lab in zip(rows, labels):
        lab_i = int(lab)
        by_cluster.setdefault(lab_i, []).append(r)

    for cid in cluster_ids:
        members = by_cluster.get(cid, [])[:20]
        if not members:
            continue
        lines = []
        for m in members:
            lines.append(
                f"id={m['tid']} title={m['title']!r} summary={(m['summary_text'] or '')[:400]}"
            )
        prompt = f"""Here are the titles and summaries of the top {len(members)} videos in cluster #{cid}.
Give this cluster:
1. A catchy descriptive name (max 6 words)
2. A 1-sentence description of the theme
3. A suggested teaching order (list of video IDs, simplest first)
Output as JSON: {{"name": "...", "description": "...", "teaching_order": [...]}}
"""
        user = "\n".join(lines) + "\n\n" + prompt
        try:
            resp = client.chat.completions.create(
                model=model_lm,
                messages=[
                    {"role": "system", "content": "You reply with JSON only."},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
            )
            raw = (resp.choices[0].message.content or "").strip()
            obj = _extract_json(raw)
            names[str(cid)] = obj
            name = obj.get("name") or f"cluster_{cid}"
            conn.execute(
                "UPDATE videos SET cluster_name = ? WHERE cluster_id = ?",
                (name, cid),
            )
        except Exception as e:
            logger.exception("Cluster name failed for %s: %s", cid, e)
            names[str(cid)] = {"name": f"cluster_{cid}", "description": "", "teaching_order": []}

    conn.commit()
    conn.close()

    (DATA / "cluster_names.json").write_text(
        json.dumps(names, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="playlist_archive.db")
    p.add_argument(
        "--n-clusters",
        type=int,
        default=None,
        help="KMeans cluster count (default: 15 or CLUSTER_N_CLUSTERS env)",
    )
    args = p.parse_args()
    run_clustering(db_path=args.db, n_clusters=args.n_clusters)


if __name__ == "__main__":
    main()

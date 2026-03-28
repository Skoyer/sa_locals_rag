# Cursor Build Instructions — SA Locals RAG Enhanced Pipeline

## Adaptation (this repo)

- **Metadata table:** `videos` (PK `url`), not `lessons`. All new columns live on `videos`.
- **Transcripts:** `JOIN videos` + `transcripts` on `url = video_url`; read text from `transcripts.transcript_path` JSON via `load_transcript_text()` in `pipeline/llm_pipeline.py`.
- **FTS5:** `videos_fts` with `content='videos'`, not `lessons_fts`.
- **IDs:** Logical key `videos.url`; use `transcripts.id` (int) for embeddings, cluster CSV, word cloud filenames, `failed_ids.txt`, and `web/data.js` `video_id`.

---

## Overview & Ground Rules

- This project uses Python 3.11+, SQLite with FTS5, LM Studio (local LLM via OpenAI-compatible API), and a Tkinter/Rich status window.
- All new files go into clearly named subdirectories: `pipeline/`, `nlp/`, `wordclouds/`, `ui/`, `web/`.
- Every script must be idempotent — re-running it should never duplicate data.
- All LLM calls must include a `{}` fallback on failure and log failed transcript IDs to `logs/failed_ids.txt`.
- Use the existing `db.py` for all SQLite interactions. Extend it; do not replace it.
- Target model: Qwen2.5-14B-Instruct or Llama-3.1-8B-Instruct via LM Studio at `http://localhost:1234/v1`.
- **LM context (4096 tokens typical):** each transcript is truncated before sending (`LLM_MAX_TRANSCRIPT_CHARS`, default `2500`). If LM Studio still returns 400 context errors, lower that value or set `LLM_BATCH_SIZE=1` or `2`. Increase truncation if you load a model with a larger context. **Sentence-transformers** may log `UNEXPECTED` keys when loading `all-MiniLM-L6-v2`; safe to ignore.

---

## PHASE 1 — Database Schema Migration

**File to modify:** `db.py`

Add columns to `videos` (PRAGMA + `ALTER TABLE ... ADD COLUMN` pattern). Column list matches the original `lessons` spec: `summary_text`, `core_lesson`, `key_concepts` (JSON text), `complexity_indicators`, `primary_topics`, `secondary_topics`, `persuasion_techniques`, `psychology_concepts`, `difficulty`, `prerequisites`, `builds_toward`, `related_lessons_keywords`, `tone`, `use_cases`, `is_persuasion_focused`, `topic_buckets`, `cluster_id`, `cluster_name`, `wordcloud_path`, `publish_date`.

FTS5:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
  url UNINDEXED,
  title,
  summary_text,
  key_concepts,
  related_lessons_keywords,
  content='videos',
  content_rowid='rowid'
);
```

Triggers on `videos` for INSERT/UPDATE/DELETE; then `INSERT INTO videos_fts(videos_fts) VALUES('rebuild')` as needed.

---

## PHASE 2 — Enhanced 2-Pass LLM Pipeline

**File:** `pipeline/llm_pipeline.py`

- JOIN `videos` + `transcripts`; load transcript JSON with `load_transcript_text` (supports wrapper `whisper_result` with `text` or `segments`, and raw Whisper shapes).
- Few-shot prompting; batches of 3; Pass 1 then Pass 2; write to `videos` immediately.
- `--limit`, `--retry-failed` (reads `logs/failed_ids.txt` as `transcripts.id` integers).

---

## PHASE 3 — Live Status Window

**File:** `ui/status_window.py` — Tkinter + Rich fallback; `StatusWindow` API per plan.

---

## PHASE 4 — Zero-Shot Multi-Label Classification

**File:** `nlp/topic_classifier.py` — batches of 10; `topic_buckets` on `videos`.

---

## PHASE 5 — Embedding-Based Clustering

**File:** `nlp/cluster_videos.py` — `sentence-transformers` `all-MiniLM-L6-v2`, **KMeans** (default 15 clusters; `CLUSTER_N_CLUSTERS` env or `--n-clusters`), `data/embeddings.npy`, `data/embedding_ids.json` (`transcripts.id` order), `cluster_id`/`cluster_name` on `videos`, `data/clusters.csv`, `data/cluster_names.json`.

---

## PHASE 6 — Hierarchical Topic Tree

**File:** `nlp/build_topic_tree.py` — `data/topic_tree.json`; `recommended_video_ids` as `transcripts.id` list.

---

## PHASE 7 — Word Clouds

**File:** `wordclouds/generate_wordclouds.py` — per-video `wordclouds/per_video/{transcripts.id}.png`, cluster/topic/master paths; `get_wordcloud_path(transcript_id)`.

---

## PHASE 8 — Summary Web Page

**File:** `web/summary_page.py` — generates `web/index.html` + `web/data.js` (includes `url` and transcript `id`).

---

## PHASE 9 — Master Runner

**File:** `run_full_pipeline.py` — orchestrates phases; flags `--skip-llm`, `--skip-clusters`, `--skip-wordclouds`, `--retry-failed`, `--rebuild-web`.

---

## PHASE 10 — requirements.txt

Merge ML/UI deps with existing downloader stack (yt-dlp, playwright, whisper, etc.).

---

## File/Folder Structure (adapted)

```
pipeline/llm_pipeline.py
nlp/{topic_classifier,cluster_videos,build_topic_tree}.py
wordclouds/generate_wordclouds.py + per_video/, clusters/, topics/
ui/status_window.py
web/{summary_page.py,index.html,data.js}
data/{embeddings.npy,embedding_ids.json,clusters.csv,cluster_names.json,topic_tree.json}
logs/failed_ids.txt
run_full_pipeline.py
db.py
```

---

## Testing Checkpoints

- Phase 1: `PRAGMA table_info(videos)`; `videos_fts` + triggers.
- Phase 2: `--limit 3`; DB updated; failures logged.
- Phases 3–9: status UI, topic buckets, clusters CSV, topic tree, word clouds, static web, full runner.

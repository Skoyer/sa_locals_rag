# Database Reference

SA Locals RAG uses a single **SQLite 3** file (`playlist_archive.db` by default) with three tables: `videos`, `transcripts`, and `videos_fts`.

---

## Tables

### `videos`

The primary table. Each row represents one Locals.com post/video.

| Column | Type | Description |
|---|---|---|
| `url` | TEXT PK | Locals.com post URL (unique identifier) |
| `title` | TEXT | Video/post title |
| `description` | TEXT | Post description |
| `downloaded_at` | TEXT | ISO 8601 UTC timestamp of last download attempt |
| `status` | TEXT | `downloaded`, `failed`, or `skipped` |
| `transcribed` | INTEGER | `1` if Whisper transcript exists, `0` otherwise |
| `duration_seconds` | INTEGER | Video duration (if extractable) |
| `category` | TEXT | Post category (default: `Micro Lessons`) |
| `tags` | TEXT | Comma-separated tags |
| `topics` | TEXT | Raw topic strings |
| `file_path` | TEXT | Absolute path to local video file |
| `posted_at` | TEXT | Original post date on Locals.com |
| `summary_text` | TEXT | LLM-generated summary |
| `core_lesson` | TEXT | Single most important takeaway |
| `key_concepts` | TEXT | LLM-extracted key concepts |
| `complexity_indicators` | TEXT | Signals of content complexity |
| `primary_topics` | TEXT | Top-level topic categories |
| `secondary_topics` | TEXT | Supporting topics |
| `persuasion_techniques` | TEXT | Persuasion/rhetoric techniques |
| `psychology_concepts` | TEXT | Psychological principles referenced |
| `difficulty` | TEXT | Beginner / Intermediate / Advanced |
| `prerequisites` | TEXT | Assumed background knowledge |
| `builds_toward` | TEXT | What this video leads to |
| `related_lessons_keywords` | TEXT | Keywords for linking related videos |
| `tone` | TEXT | Content tone descriptor |
| `use_cases` | TEXT | Practical applications |
| `is_persuasion_focused` | INTEGER | Boolean flag |
| `topic_buckets` | TEXT | Playlist bucket categories |
| `cluster_id` | INTEGER | Clustering group number |
| `cluster_name` | TEXT | Cluster label |
| `wordcloud_path` | TEXT | Path to generated word cloud image |
| `publish_date` | TEXT | Normalized publish date |

---

### `transcripts`

Stores metadata about each Whisper-generated transcript file.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `video_url` | TEXT UNIQUE | Foreign key → `videos.url` |
| `transcript_path` | TEXT | Absolute path to the `.txt` transcript file |
| `model_name` | TEXT | Whisper model used (e.g., `base`) |
| `created_at` | TEXT | ISO 8601 creation timestamp |

---

### `videos_fts` (FTS5 Virtual Table)

An FTS5 external-content virtual table that mirrors key text columns from `videos` for full-text search.

**Indexed columns**: `url`, `title`, `summary_text`, `key_concepts`, `related_lessons_keywords`

Three SQLite triggers (`videos_ai`, `videos_ad`, `videos_au`) automatically keep the FTS index in sync with inserts, deletes, and updates on `videos`.

---

## Useful Queries

### Check pipeline status
```sql
SELECT status, COUNT(*) as count FROM videos GROUP BY status;
```

### Find un-transcribed downloaded videos
```sql
SELECT url, title FROM videos
WHERE status = 'downloaded' AND transcribed = 0;
```

### Full-text search across titles and summaries
```sql
SELECT v.url, v.title, v.summary_text
FROM videos_fts
JOIN videos v ON v.rowid = videos_fts.rowid
WHERE videos_fts MATCH 'persuasion cognitive bias'
ORDER BY rank;
```

### List all cluster groups
```sql
SELECT cluster_id, cluster_name, COUNT(*) as video_count
FROM videos
WHERE cluster_id IS NOT NULL
GROUP BY cluster_id, cluster_name
ORDER BY cluster_id;
```

### Find videos by difficulty
```sql
SELECT title, difficulty, primary_topics
FROM videos
WHERE difficulty = 'Beginner'
ORDER BY posted_at;
```

### Export all LLM-analyzed videos
```sql
SELECT url, title, summary_text, core_lesson, primary_topics,
       difficulty, cluster_name, is_persuasion_focused
FROM videos
WHERE summary_text IS NOT NULL
ORDER BY posted_at;
```

---

## Schema Migrations

The `_migrate_video_columns()` function in `db.py` automatically adds missing columns to an existing database using `ALTER TABLE ... ADD COLUMN`. You never need to manually run migrations — simply running any pipeline script against an older database will apply them.

---

## Backup

Because the database is a single file, backups are trivial:

```bash
cp playlist_archive.db playlist_archive.db.bak

# Or use SQLite's online backup API:
sqlite3 playlist_archive.db ".backup 'backup.db'"
```

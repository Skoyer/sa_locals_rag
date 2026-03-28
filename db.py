"""SQLite storage for video metadata."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# RAG / analysis columns (all TEXT except integers noted)
_VIDEO_RAG_COLUMNS: list[tuple[str, str]] = [
    ("summary_text", "TEXT"),
    ("core_lesson", "TEXT"),
    ("key_concepts", "TEXT"),
    ("complexity_indicators", "TEXT"),
    ("primary_topics", "TEXT"),
    ("secondary_topics", "TEXT"),
    ("persuasion_techniques", "TEXT"),
    ("psychology_concepts", "TEXT"),
    ("difficulty", "TEXT"),
    ("prerequisites", "TEXT"),
    ("builds_toward", "TEXT"),
    ("related_lessons_keywords", "TEXT"),
    ("tone", "TEXT"),
    ("use_cases", "TEXT"),
    ("is_persuasion_focused", "INTEGER"),
    ("topic_buckets", "TEXT"),
    ("cluster_id", "INTEGER"),
    ("cluster_name", "TEXT"),
    ("wordcloud_path", "TEXT"),
    ("publish_date", "TEXT"),
]


def _migrate_video_columns(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA table_info(videos)")
    existing = {row[1] for row in cur.fetchall()}
    migrations: list[tuple[str, str]] = []
    if "transcribed" not in existing:
        migrations.append(("transcribed", "INTEGER DEFAULT 0"))
    if "duration_seconds" not in existing:
        migrations.append(("duration_seconds", "INTEGER"))
    if "category" not in existing:
        migrations.append(("category", "TEXT DEFAULT 'Micro Lessons'"))
    if "tags" not in existing:
        migrations.append(("tags", "TEXT"))
    if "topics" not in existing:
        migrations.append(("topics", "TEXT"))
    if "file_path" not in existing:
        migrations.append(("file_path", "TEXT"))
    if "posted_at" not in existing:
        migrations.append(("posted_at", "TEXT"))
    for name, col_def in _VIDEO_RAG_COLUMNS:
        if name not in existing:
            migrations.append((name, col_def))
    for name, col_def in migrations:
        conn.execute(f"ALTER TABLE videos ADD COLUMN {name} {col_def}")
    if migrations:
        conn.commit()


def _ensure_videos_fts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
          url UNINDEXED,
          title,
          summary_text,
          key_concepts,
          related_lessons_keywords,
          content='videos',
          content_rowid='rowid'
        )
        """
    )
    # External-content FTS5: keep index in sync with videos
    conn.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS videos_ai AFTER INSERT ON videos BEGIN
          INSERT INTO videos_fts(rowid, url, title, summary_text, key_concepts, related_lessons_keywords)
          VALUES (new.rowid, new.url, new.title, new.summary_text, new.key_concepts, new.related_lessons_keywords);
        END;
        CREATE TRIGGER IF NOT EXISTS videos_ad AFTER DELETE ON videos BEGIN
          INSERT INTO videos_fts(videos_fts, rowid, url, title, summary_text, key_concepts, related_lessons_keywords)
          VALUES('delete', old.rowid, old.url, old.title, old.summary_text, old.key_concepts, old.related_lessons_keywords);
        END;
        CREATE TRIGGER IF NOT EXISTS videos_au AFTER UPDATE ON videos BEGIN
          INSERT INTO videos_fts(videos_fts, rowid, url, title, summary_text, key_concepts, related_lessons_keywords)
          VALUES('delete', old.rowid, old.url, old.title, old.summary_text, old.key_concepts, old.related_lessons_keywords);
          INSERT INTO videos_fts(rowid, url, title, summary_text, key_concepts, related_lessons_keywords)
          VALUES (new.rowid, new.url, new.title, new.summary_text, new.key_concepts, new.related_lessons_keywords);
        END;
        """
    )
    conn.commit()
    try:
        conn.execute("INSERT INTO videos_fts(videos_fts) VALUES('rebuild')")
        conn.commit()
    except sqlite3.OperationalError:
        pass


def init_db(path: str = "playlist_archive.db") -> None:
    """Create the database file and videos table if they do not exist."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                url TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                downloaded_at TEXT,
                status TEXT,
                transcribed INTEGER DEFAULT 0,
                duration_seconds INTEGER,
                category TEXT DEFAULT 'Micro Lessons',
                tags TEXT,
                topics TEXT
            )
            """
        )
        conn.commit()
        _migrate_video_columns(conn)

        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transcripts'"
        )
        if not cur.fetchone():
            conn.execute(
                """
                CREATE TABLE transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_url TEXT NOT NULL UNIQUE,
                    transcript_path TEXT NOT NULL,
                    model_name TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        _ensure_videos_fts(conn)
    finally:
        conn.close()


def get_downloaded_urls(conn: sqlite3.Connection) -> set[str]:
    """Return the set of video URLs that are successfully downloaded.

    We intentionally do NOT include failed rows so the downloader can retry them
    after improvements/fixes.
    """
    cur = conn.execute("SELECT url FROM videos WHERE status = 'downloaded'")
    return {row[0] for row in cur.fetchall()}


def insert_video(
    conn: sqlite3.Connection,
    url: str,
    title: str,
    description: str,
    status: str,
    file_path: str | None = None,
    posted_at: str | None = None,
) -> None:
    """Insert or update a video row; downloaded_at is set to now (ISO 8601).

    Preserves RAG/analysis columns when updating an existing URL (UPSERT).
    """
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO videos (
            url,
            title,
            description,
            downloaded_at,
            status,
            transcribed,
            duration_seconds,
            category,
            tags,
            topics,
            file_path,
            posted_at
        )
        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            COALESCE((SELECT transcribed FROM videos WHERE url = ?), 0),
            COALESCE((SELECT duration_seconds FROM videos WHERE url = ?), NULL),
            COALESCE((SELECT category FROM videos WHERE url = ?), 'Micro Lessons'),
            COALESCE((SELECT tags FROM videos WHERE url = ?), ''),
            COALESCE((SELECT topics FROM videos WHERE url = ?), ''),
            COALESCE(?, (SELECT file_path FROM videos WHERE url = ?)),
            COALESCE(?, (SELECT posted_at FROM videos WHERE url = ?))
        )
        ON CONFLICT(url) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            downloaded_at = excluded.downloaded_at,
            status = excluded.status,
            transcribed = MAX(videos.transcribed, excluded.transcribed),
            duration_seconds = COALESCE(excluded.duration_seconds, videos.duration_seconds),
            category = excluded.category,
            tags = excluded.tags,
            topics = excluded.topics,
            file_path = COALESCE(excluded.file_path, videos.file_path),
            posted_at = COALESCE(excluded.posted_at, videos.posted_at),
            summary_text = videos.summary_text,
            core_lesson = videos.core_lesson,
            key_concepts = videos.key_concepts,
            complexity_indicators = videos.complexity_indicators,
            primary_topics = videos.primary_topics,
            secondary_topics = videos.secondary_topics,
            persuasion_techniques = videos.persuasion_techniques,
            psychology_concepts = videos.psychology_concepts,
            difficulty = videos.difficulty,
            prerequisites = videos.prerequisites,
            builds_toward = videos.builds_toward,
            related_lessons_keywords = videos.related_lessons_keywords,
            tone = videos.tone,
            use_cases = videos.use_cases,
            is_persuasion_focused = videos.is_persuasion_focused,
            topic_buckets = videos.topic_buckets,
            cluster_id = videos.cluster_id,
            cluster_name = videos.cluster_name,
            wordcloud_path = videos.wordcloud_path,
            publish_date = videos.publish_date
        """,
        (
            url,
            title,
            description,
            now,
            status,
            url,
            url,
            url,
            url,
            url,
            file_path,
            url,
            posted_at,
            url,
        ),
    )
    conn.commit()


def insert_transcript(
    conn: sqlite3.Connection,
    video_url: str,
    transcript_path: str,
    model_name: str | None,
    created_at: str,
) -> None:
    """Insert or replace a transcript row (one per video_url via UNIQUE)."""
    conn.execute(
        """
        INSERT INTO transcripts (video_url, transcript_path, model_name, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(video_url) DO UPDATE SET
            transcript_path = excluded.transcript_path,
            model_name = excluded.model_name,
            created_at = excluded.created_at
        """,
        (video_url, transcript_path, model_name, created_at),
    )
    conn.commit()


def mark_video_transcribed(conn: sqlite3.Connection, video_url: str) -> None:
    """Set transcribed=1 for a downloaded video."""
    conn.execute(
        "UPDATE videos SET transcribed = 1 WHERE url = ?",
        (video_url,),
    )
    conn.commit()


if __name__ == "__main__":
    init_db()
    c = sqlite3.connect("playlist_archive.db")
    try:
        cols = c.execute("PRAGMA table_info(videos)").fetchall()
        print("videos columns:", len(cols))
        fts = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='videos_fts'"
        ).fetchone()
        print("videos_fts:", fts)
    finally:
        c.close()

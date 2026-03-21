"""SQLite storage for video metadata."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


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
    finally:
        # Lightweight migration for existing DBs: add any missing columns.
        cur = conn.execute("PRAGMA table_info(videos)")
        existing_cols = {row[1] for row in cur.fetchall()}
        migrations: list[tuple[str, str]] = []
        if "transcribed" not in existing_cols:
            migrations.append(("transcribed", "INTEGER DEFAULT 0"))
        if "duration_seconds" not in existing_cols:
            migrations.append(("duration_seconds", "INTEGER"))
        if "category" not in existing_cols:
            migrations.append(("category", "TEXT DEFAULT 'Micro Lessons'"))
        if "tags" not in existing_cols:
            migrations.append(("tags", "TEXT"))
        if "topics" not in existing_cols:
            migrations.append(("topics", "TEXT"))
        if "file_path" not in existing_cols:
            migrations.append(("file_path", "TEXT"))
        if "posted_at" not in existing_cols:
            migrations.append(("posted_at", "TEXT"))
        for name, col_def in migrations:
            conn.execute(f"ALTER TABLE videos ADD COLUMN {name} {col_def}")
        if migrations:
            conn.commit()

        # Transcripts produced by the transcription pipeline (one row per video_url by default).
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
    """Insert or replace a video row; downloaded_at is set to now (ISO 8601).

    Future-facing fields:
    - transcribed: 0/1 (default 0, set by analysis pipeline later)
    - duration_seconds: nullable integer (filled when known)
    - category: text, defaults to 'Micro Lessons'
    - tags/topics: free-form, multi-value supported via delimited or JSON text
    """
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT OR REPLACE INTO videos (
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

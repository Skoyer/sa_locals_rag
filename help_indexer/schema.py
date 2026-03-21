"""SQLite schema: videos, transcript_segments, FTS5 + sync triggers."""
from __future__ import annotations

import sqlite3
from pathlib import Path


# PRAGMA foreign_keys must be set per connection (not only inside executescript).
DDL = """
CREATE TABLE IF NOT EXISTS videos(
  id INTEGER PRIMARY KEY,
  external_id TEXT NOT NULL UNIQUE,
  title TEXT,
  description TEXT,
  filename TEXT,
  duration_sec INTEGER
);

CREATE TABLE IF NOT EXISTS transcript_segments(
  id INTEGER PRIMARY KEY,
  video_id INTEGER NOT NULL,
  start_sec REAL NOT NULL,
  end_sec REAL NOT NULL,
  text TEXT NOT NULL,
  FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS transcript_segments_fts
USING fts5(
  text,
  content='transcript_segments',
  content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS transcript_segments_ai
AFTER INSERT ON transcript_segments
BEGIN
  INSERT INTO transcript_segments_fts(rowid, text)
  VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS transcript_segments_ad
AFTER DELETE ON transcript_segments
BEGIN
  INSERT INTO transcript_segments_fts(transcript_segments_fts, rowid, text)
  VALUES('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS transcript_segments_au
AFTER UPDATE ON transcript_segments
BEGIN
  INSERT INTO transcript_segments_fts(transcript_segments_fts, rowid, text)
  VALUES('delete', old.id, old.text);
  INSERT INTO transcript_segments_fts(rowid, text)
  VALUES (new.id, new.text);
END;
"""


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """Create DB file, tables, FTS, and triggers. Returns an open connection."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    conn.commit()
    return conn


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Rebuild FTS index from transcript_segments (e.g. after manual DB edits)."""
    conn.execute(
        "INSERT INTO transcript_segments_fts(transcript_segments_fts) VALUES('rebuild')"
    )
    conn.commit()

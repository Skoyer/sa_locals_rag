"""Run one download cycle and exit (for debugging). No scheduler."""
import sqlite3
from datetime import datetime, timezone

import config
import db
from downloader import download_one_if_any


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {msg}")


if __name__ == "__main__":
    log("--- One-off run (debug) ---")
    db.init_db(config.DB_PATH)
    conn = sqlite3.connect(config.DB_PATH)
    try:
        download_one_if_any(conn, config.PLAYLIST_URL or "", config.OUTPUT_DIR)
    except Exception as e:
        log(f"ERROR: {e}")
    finally:
        conn.close()
    log("--- Done ---")

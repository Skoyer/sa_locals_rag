"""Hourly playlist downloader – entry point."""
import sqlite3
import time
from datetime import datetime, timezone

import schedule

import config
import db
from downloader import download_one_if_any


def _log(msg: str) -> None:
    """Print a timestamped line."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}")


def hourly_job():
    """Download at most one new video from the playlist and store metadata in SQLite."""
    _log("--- Scheduled job starting ---")
    conn = sqlite3.connect(config.DB_PATH)
    try:
        download_one_if_any(
            conn,
            config.PLAYLIST_URL or "",
            config.OUTPUT_DIR,
        )
    except Exception as e:
        _log(f"ERROR: Hourly job failed: {e}")
    finally:
        conn.close()
    _log("--- Scheduled job finished ---")


def main():
    print("hello")
    db.init_db(config.DB_PATH)
    _log("Database ready.")
    minutes = max(1, int(getattr(config, "RUN_EVERY_MINUTES", 5)))
    _log(f"Running first download now (then every {minutes} minutes).")
    hourly_job()
    schedule.every(minutes).minutes.do(hourly_job)
    next_run = schedule.next_run()
    if next_run:
        # schedule uses local time; convert to UTC for consistent logging
        local_tz = datetime.now().astimezone().tzinfo
        next_run_utc = next_run.replace(tzinfo=local_tz).astimezone(timezone.utc)
        _log(
            f"Next run at {next_run_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}. Waiting..."
        )
    else:
        _log(f"Next run in {minutes} minutes. Waiting...")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()

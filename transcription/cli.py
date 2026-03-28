"""CLI: init DB, optional orphan sync, run transcription pipeline."""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

import db
from transcription import config
from transcription.pipeline import process
from transcription.sync import sync_orphan_downloads


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Transcribe downloaded videos with Whisper (uses playlist_archive.db).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of candidate videos to process (default: no limit)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Whisper model name (default: WHISPER_MODEL env or 'small')",
    )
    parser.add_argument(
        "--sync-orphans",
        action="store_true",
        help="Insert DB rows for video files under OUTPUT_DIR not referenced by any file_path",
    )
    args = parser.parse_args(argv)

    root = config.project_root()
    db_path = Path(config.DB_PATH)
    if not db_path.is_absolute():
        db_path = (root / db_path).resolve()

    db.init_db(str(db_path))
    conn = sqlite3.connect(str(db_path))
    try:
        if args.sync_orphans:
            out = Path(config.OUTPUT_DIR)
            if not out.is_absolute():
                out = (root / out).resolve()
            else:
                out = out.resolve()
            added = sync_orphan_downloads(conn, root.resolve(), out)
            logging.info("sync_orphan_downloads: registered %s file(s)", added)

        ok, bad = process(conn, model_name=args.model, limit=args.limit)
        logging.info("Transcription finished: %s ok, %s failed or skipped", ok, bad)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

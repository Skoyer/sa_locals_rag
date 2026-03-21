"""CLI: index | search | serve | rebuild-fts."""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

from help_indexer import config
from help_indexer.pipeline import run_pipeline
from help_indexer.schema import init_db, rebuild_fts
from help_indexer.search import search_segments


def _db_path() -> Path:
    p = Path(config.DB_PATH)
    if not p.is_absolute():
        p = config.project_root() / p
    return p.resolve()


def _media_root() -> Path:
    p = Path(config.MEDIA_DIR)
    if not p.is_absolute():
        p = config.project_root() / p
    return p.resolve()


def cmd_index(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    conn = init_db(_db_path())
    try:
        ok, fail = run_pipeline(
            conn,
            _media_root(),
            model_name=args.model or config.WHISPER_MODEL,
            limit=args.limit,
        )
        print(f"Done. Success: {ok}, failed: {fail}")
        return 0 if fail == 0 else 1
    finally:
        conn.close()


def cmd_search(args: argparse.Namespace) -> int:
    conn = init_db(_db_path())
    try:
        mode = "strict" if args.strict else "loose"
        rows = search_segments(
            conn,
            args.query,
            limit=args.limit,
            match_mode=mode,
        )
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    finally:
        conn.close()


def cmd_rebuild_fts(_args: argparse.Namespace) -> int:
    conn = init_db(_db_path())
    try:
        rebuild_fts(conn)
        print("FTS rebuild complete.")
        return 0
    finally:
        conn.close()


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError as e:
        print("Install uvicorn: pip install uvicorn[standard]", file=sys.stderr)
        raise SystemExit(1) from e
    uvicorn.run(
        "help_indexer.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Help indexer: Whisper to SQLite + FTS5 (separate from playlist DB).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Scan HELP_MEDIA_DIR and transcribe into help_videos.db")
    p_index.add_argument("--limit", type=int, default=None, help="Max files to process")
    p_index.add_argument(
        "--model",
        type=str,
        default=None,
        help="Whisper model (default: HELP_WHISPER_MODEL or small)",
    )
    p_index.set_defaults(func=cmd_index)

    p_search = sub.add_parser("search", help="FTS search (JSON array to stdout)")
    p_search.add_argument("query", type=str, help="Search query")
    p_search.add_argument("--limit", type=int, default=20)
    p_search.add_argument(
        "--strict",
        action="store_true",
        help="FTS5 AND semantics (space = all terms); default is loose prefix/OR for compounds",
    )
    p_search.set_defaults(func=cmd_search)

    p_rebuild = sub.add_parser("rebuild-fts", help="Rebuild FTS index from transcript_segments")
    p_rebuild.set_defaults(func=cmd_rebuild_fts)

    p_serve = sub.add_parser("serve", help="Run FastAPI + uvicorn (POST /index, GET /search)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

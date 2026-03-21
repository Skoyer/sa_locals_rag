"""Entrypoint: python run_help_indexer.py index|search|serve|rebuild-fts ..."""
from help_indexer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

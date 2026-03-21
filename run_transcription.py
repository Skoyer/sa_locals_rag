"""Thin entrypoint: python run_transcription.py [--limit N] [--model small] [--sync-orphans]"""
from transcription.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

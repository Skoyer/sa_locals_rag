"""Single entry: migrate DB, optional status UI, LLM, NLP, word clouds, web export."""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import db


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="SA Locals RAG full pipeline")
    p.add_argument("--db", default="playlist_archive.db")
    p.add_argument("--project-root", type=Path, default=None)
    p.add_argument("--skip-llm", action="store_true", help="Skip LLM phases 2–4")
    p.add_argument("--skip-clusters", action="store_true", help="Skip phase 5")
    p.add_argument("--skip-wordclouds", action="store_true", help="Skip phase 7")
    p.add_argument(
        "--retry-failed",
        action="store_true",
        help="LLM only: process ids in logs/failed_ids.txt",
    )
    p.add_argument(
        "--rebuild-web",
        action="store_true",
        help="Only regenerate web/index.html and web/data.js",
    )
    p.add_argument("--limit", type=int, default=None, help="LLM: max videos to process")
    p.add_argument(
        "--offset",
        type=int,
        default=0,
        help="LLM: skip first N eligible videos before --limit",
    )
    p.add_argument(
        "--only-missing",
        action="store_true",
        help="LLM: only rows without core_lesson (next batch without redoing done work)",
    )
    args = p.parse_args()
    root = args.project_root or Path.cwd()
    db_path = str(Path(args.db).resolve())

    db.init_db(db_path)

    if args.rebuild_web:
        from web import summary_page

        summary_page.write_summary_page(db_path)
        print("Rebuilt web/ export.")
        return

    from nlp.build_topic_tree import run_build_topic_tree
    from nlp.cluster_videos import run_clustering
    from nlp.topic_classifier import run_topic_classifier
    from pipeline import llm_pipeline
    from ui.status_window import StatusWindow
    from web import summary_page
    from wordclouds import generate_wordclouds

    status = StatusWindow()
    status.start()

    t0 = time.perf_counter()

    if not args.skip_llm:
        llm_pipeline.run_llm_pipeline(
            db_path=db_path,
            limit=args.limit,
            offset=args.offset,
            only_missing=args.only_missing,
            retry_failed=args.retry_failed,
            project_root=root,
            status=status,
        )
        run_topic_classifier(db_path=db_path)
    else:
        logging.info("Skipping phases 2–4 (--skip-llm)")

    if not args.skip_clusters:
        run_clustering(db_path=db_path)
    else:
        logging.info("Skipping phase 5 clustering (--skip-clusters)")

    run_build_topic_tree(db_path=db_path)

    if not args.skip_wordclouds:
        generate_wordclouds.run_wordclouds(db_path=db_path)
    else:
        logging.info("Skipping word clouds (--skip-wordclouds)")

    summary_page.write_summary_page(db_path)

    status.stop()
    elapsed = time.perf_counter() - t0
    print(
        f"Done in {elapsed:.1f}s. Open web/index.html (file://) for the static summary."
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)

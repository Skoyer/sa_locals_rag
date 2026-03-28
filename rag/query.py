"""
End-to-end RAG query: search → prompt → LLM answer.

Usage:
    from rag.query import ask
    answer = ask("What does Scott Adams say about persuasion ethics?")
    print(answer)
"""
from __future__ import annotations

import os
import requests

from rag.prompt_builder import build_messages, select_hits
from rag.llm_client import get_client


INDEXER_URL = os.getenv("INDEXER_URL", "http://localhost:8000")
SEARCH_LIMIT = int(os.getenv("RAG_SEARCH_LIMIT", "15"))
MAX_PROMPT_HITS = int(os.getenv("RAG_MAX_PROMPT_HITS", "8"))


def search(question: str, limit: int = SEARCH_LIMIT) -> list[dict]:
    """Call the help_indexer /search endpoint."""
    resp = requests.get(
        f"{INDEXER_URL}/search",
        params={"q": question, "limit": limit, "mode": "loose"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def ask(
    question: str,
    *,
    stream: bool = False,
    debug: bool = False,
) -> str:
    """
    Full RAG pipeline:
      1. Search transcript segments
      2. Deduplicate and select best hits
      3. Build grounded prompt
      4. Call LLM and return answer

    Parameters
    ----------
    question : str   — plain-language question
    stream   : bool  — if True, prints tokens as they arrive and returns final string
    debug    : bool  — if True, prints full prompt payload before calling LLM
    """
    # 1. Retrieve
    hits = search(question)

    # 2. Select and deduplicate
    selected = select_hits(hits, max_hits=MAX_PROMPT_HITS)

    # 3. Build prompt
    messages = build_messages(question, selected)

    if debug:
        from rag.prompt_builder import preview
        preview(question, selected)

    # 4. Call LLM
    client = get_client()
    print(f"[RAG] Using {client.model_name()} | {len(selected)} segments retrieved")

    if stream:
        full = []
        for token in client.chat(messages, stream=True):
            print(token, end="", flush=True)
            full.append(token)
        print()
        return "".join(full)

    return client.chat(messages)

"""Small FastAPI service: POST /index, GET /search."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from help_indexer import config
from help_indexer.pipeline import run_pipeline
from help_indexer.schema import init_db, rebuild_fts
from help_indexer.search import MatchMode, search_segments


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


app = FastAPI(
    title="Help media FTS search",
    description="Index local media with Whisper; search transcript segments.",
)


@app.get("/")
def get_root() -> dict[str, str]:
    """Avoid bare 404 on /; interactive API is under /docs."""
    return {
        "message": "Help indexer API",
        "docs": "/docs",
        "search": "/search?q=your+terms",
        "index": "POST /index",
        "rebuild_fts": "POST /rebuild-fts",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


class IndexRequest(BaseModel):
    limit: int | None = Field(
        default=None,
        description="Max files to process (None = all)",
    )


class SearchHit(BaseModel):
    video_id: int
    title: str | None
    filename: str | None = None
    external_id: str | None = None
    segment_id: int
    start_sec: float
    end_sec: float
    snippet_html: str
    score: float


class SearchMode(str, Enum):
    """FTS query interpretation (OpenAPI-friendly; maps to search.MatchMode)."""

    loose = "loose"
    strict = "strict"
    raw = "raw"


@app.post("/index")
def post_index(body: IndexRequest | None = None) -> dict[str, Any]:
    """(Re)run discovery + Whisper + DB upsert over HELP_MEDIA_DIR."""
    body = body or IndexRequest()
    conn = init_db(_db_path())
    try:
        ok, fail = run_pipeline(
            conn,
            _media_root(),
            model_name=config.WHISPER_MODEL,
            limit=body.limit,
        )
        return {"ok": True, "processed_ok": ok, "failed": fail}
    finally:
        conn.close()


@app.post("/rebuild-fts")
def post_rebuild_fts() -> dict[str, str]:
    conn = init_db(_db_path())
    try:
        rebuild_fts(conn)
        return {"ok": "rebuilt"}
    finally:
        conn.close()


@app.get("/search", response_model=list[SearchHit])
def get_search(
    q: str = Query(..., min_length=1, description="Search text (default: loose prefix/OR)"),
    limit: int = Query(20, ge=1, le=200),
    mode: SearchMode = Query(
        SearchMode.loose,
        description="loose = prefix/OR (matches compounds like brainwashing); strict = FTS5 AND",
    ),
) -> list[SearchHit]:
    conn = init_db(_db_path())
    try:
        rows = search_segments(
            conn,
            q,
            limit=limit,
            match_mode=cast(MatchMode, mode.value),
        )
        return [SearchHit(**r) for r in rows]
    finally:
        conn.close()


def create_app() -> FastAPI:
    return app

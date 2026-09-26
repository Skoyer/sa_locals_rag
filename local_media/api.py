"""FastAPI app: stream local video files for the Topic Browser player."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from local_media import paths

app = FastAPI(
    title="Local media library",
    description=(
        "Streams videos from videos.file_path (including Windows C: paths) "
        "for in-browser playback. Prefer /media/video/{transcript_id}."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)


def _guess_media_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Local media library",
        "docs": "/docs",
        "health": "/media/health",
        "video": "/media/video/{transcript_id}",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/media/health")
def health() -> dict:
    db = paths.db_path()
    dl = paths.downloads_dir()
    available = 0
    missing = 0
    total_with_path = 0
    if db.is_file():
        import sqlite3

        conn = sqlite3.connect(str(db))
        try:
            rows = conn.execute(
                """
                SELECT v.file_path
                FROM videos v
                WHERE v.status = 'downloaded' AND v.file_path IS NOT NULL
                """
            ).fetchall()
            total_with_path = len(rows)
            for (fp,) in rows:
                if paths.resolve_media_path(fp):
                    available += 1
                else:
                    missing += 1
        finally:
            conn.close()
    return {
        "ok": True,
        "db_path": str(db),
        "db_exists": db.is_file(),
        "downloads_dir": str(dl),
        "downloads_dir_exists": dl.is_dir(),
        "downloaded_with_file_path": total_with_path,
        "available_locally": available,
        "missing_on_disk": missing,
    }


@app.get("/media/video/{transcript_id}")
def stream_video(transcript_id: int) -> FileResponse:
    meta = paths.lookup_by_transcript_id(transcript_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Unknown transcript id")
    resolved = meta.get("resolved_path")
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=(
                "Local file not found. Check videos.file_path / OUTPUT_DIR "
                f"(stored={meta.get('file_path')!r})."
            ),
        )
    path = Path(resolved)
    return FileResponse(
        path,
        media_type=_guess_media_type(path),
        filename=path.name,
        content_disposition_type="inline",
    )


@app.get("/media/meta/{transcript_id}")
def video_meta(transcript_id: int) -> dict:
    meta = paths.lookup_by_transcript_id(transcript_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Unknown transcript id")
    # Do not leak absolute paths to the browser beyond availability.
    return {
        "transcript_id": meta["transcript_id"],
        "title": meta["title"],
        "available": meta["available"],
        "status": meta["status"],
        "stream_url": f"/media/video/{transcript_id}" if meta["available"] else None,
    }

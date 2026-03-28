# System Architecture

SA Locals RAG is a multi-stage data pipeline that transforms raw video content into a searchable, AI-analyzed knowledge base with playlist generation.

---

## High-Level Overview

```
 Locals.com  ──►  Playlist Fetcher  ──►  Video Downloader  ──►  Audio Extractor
                                                                        │
                                                                  Whisper ASR
                                                                        │
                                                              SQLite (transcripts)
                                                                        │
                                                               LLM Pipeline
                                                            (topics, concepts, clusters)
                                                                        │
                                                          Playlist Generator
                                                                        │
                                                           Static Web UI / RAG Chat
```

---

## Detailed Data Flow

```mermaid
flowchart TD
    A["Locals.com\nPlaylist Page"] -->|"Playwright + Cookies"| B["locals_fetcher.py\nget_playlist_video_urls()"]
    B --> C["Per-video page URLs"]
    C -->|"Playwright / yt-dlp / ffmpeg"| D["downloader.py\nDownload MP4/MKV"]
    D --> E["Local video files\ndata/videos/"]
    D --> F["SQLite videos table\nstatus=downloaded"]
    E -->|"ffmpeg audio strip"| G["transcription/audio.py\nExtract WAV"]
    G --> H["Whisper ASR\ntranscription/whisper_runner.py"]
    H --> I["Transcript .txt files\ndata/transcripts/"]
    H --> J["SQLite transcripts table"]
    J --> K["pipeline/llm_pipeline.py\nLLM Analysis"]
    K --> L["RAG columns in videos table\n(summary, topics, clusters…)"]
    L --> M["Playlist Generator\nnlp/ & rag/"]
    M --> N["playlist_archive.csv"]
    N --> O["web/ Static HTML"]
    L --> P["sa_rag_chat.py\nRAG Q&A CLI"]
    O --> Q["Browser"]
    P --> Q
```

---

## Component Map

| Component | Files | Responsibility |
|---|---|---|
| **Auth** | `locals_auth.py` | Browser-based login; saves Netscape cookie file |
| **Fetcher** | `locals_fetcher.py` | Playwright crawl of playlist pages; extract post URLs and stream URLs |
| **Downloader** | `downloader.py` | Download videos via HLS (ffmpeg), yt-dlp, or direct requests |
| **Database** | `db.py` | SQLite init, migration, UPSERT helpers, FTS5 virtual table |
| **Transcription** | `transcription/` | Audio extraction (ffmpeg), Whisper ASR, DB sync |
| **LLM Pipeline** | `pipeline/llm_pipeline.py` | OpenAI calls to extract topics, clusters, difficulty, and more |
| **NLP / Clustering** | `nlp/` | Text clustering, topic bucket assignment |
| **RAG** | `rag/` | Retrieval-augmented generation helpers |
| **Web UI** | `web/` | Static HTML playlist page generation |
| **RAG Chat** | `sa_rag_chat.py` | Interactive CLI Q&A against the transcript DB |
| **Help Indexer** | `help_indexer/` | Indexes external help/docs for use in RAG context |
| **Config** | `config.py`, `.env` | Central configuration via environment variables |

---

## Storage Architecture

```mermaid
erDiagram
    videos {
        TEXT url PK
        TEXT title
        TEXT description
        TEXT downloaded_at
        TEXT status
        INTEGER transcribed
        INTEGER duration_seconds
        TEXT category
        TEXT tags
        TEXT topics
        TEXT file_path
        TEXT posted_at
        TEXT summary_text
        TEXT core_lesson
        TEXT key_concepts
        TEXT primary_topics
        TEXT secondary_topics
        TEXT persuasion_techniques
        TEXT psychology_concepts
        TEXT difficulty
        TEXT cluster_id
        TEXT cluster_name
        TEXT topic_buckets
        TEXT wordcloud_path
    }
    transcripts {
        INTEGER id PK
        TEXT video_url FK
        TEXT transcript_path
        TEXT model_name
        TEXT created_at
    }
    videos_fts {
        TEXT url
        TEXT title
        TEXT summary_text
        TEXT key_concepts
        TEXT related_lessons_keywords
    }
    videos ||--o| transcripts : "has"
    videos ||--o| videos_fts : "indexed by"
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Browser automation | Playwright (Chromium) |
| Video download | yt-dlp, ffmpeg, requests |
| Audio transcription | OpenAI Whisper (local) |
| Storage | SQLite 3 + FTS5 |
| LLM analysis | OpenAI API (GPT-4o / GPT-3.5) |
| Web UI | Static HTML/CSS/JS |
| Python runtime | Python 3.11+ |

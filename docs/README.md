# SA Locals RAG — Documentation Index

Welcome to the documentation for **SA Locals RAG**, a pipeline that ingests Scott Adams *Locals.com* video content, transcribes the audio with OpenAI Whisper, stores everything in a full-text-searchable SQLite database, analyzes transcripts with an LLM to extract topics and concepts, and generates content-similarity playlists.

---

## Contents

| Document | Description |
|---|---|
| [architecture.md](architecture.md) | System architecture, data flow, and Mermaid diagrams |
| [getting-started.md](getting-started.md) | Installation, configuration, and first run |
| [configuration.md](configuration.md) | All environment variables and config options |
| [pipeline.md](pipeline.md) | Detailed pipeline stage reference |
| [database.md](database.md) | SQLite schema, FTS5, and query examples |
| [cli-reference.md](cli-reference.md) | Every runnable script and its CLI options |
| [modules.md](modules.md) | Python module API reference |
| [web-interface.md](web-interface.md) | Static site output and future web app plans |
| [roadmap.md](roadmap.md) | Planned features (web app, auth, comments, etc.) |
| [troubleshooting.md](troubleshooting.md) | Common errors and fixes |
| [contributing.md](contributing.md) | Development setup and contribution guidelines |

---

## Quick Start (TL;DR)

```bash
# 1. Clone and install
git clone https://github.com/Skoyer/sa_locals_rag.git
cd sa_locals_rag
pip install -r requirements.txt
playwright install chromium

# 2. Configure
cp .env.example .env   # fill in LOCALS_EMAIL, LOCALS_PASSWORD, OPENAI_API_KEY

# 3. Run the full pipeline
python run_full_pipeline.py
```

See [getting-started.md](getting-started.md) for a complete walkthrough.

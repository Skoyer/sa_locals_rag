# SA Locals RAG

SA Locals RAG is a pipeline that ingests Scott Adams Locals.com videos, downloads and transcribes them, analyzes the transcripts with an LLM, and builds topic‑based playlists plus a browsable web view.

---

## Environment & Assumptions

This project was originally developed and tested on:

- OS: Windows 10/11 (PowerShell terminal)
- Python: 3.11+
- FFmpeg installed and on `PATH`
- Playwright (Chromium) installed
- Optional GPU for faster Whisper / LLM runs

Some commands in this README (for example virtualenv activation) are shown in Windows form such as:

```powershell
.venv\Scripts\activate
```

On Linux/macOS, use the appropriate shell equivalents instead, for example:

```bash
source .venv/bin/activate
```


---

## Models Used

During development, the following models/tools were used:

- **Transcription**: OpenAI Whisper (local) via the `transcription/` pipeline.
- **LLM analysis (automated pipeline)**: OpenAI API models (configurable in `OPENAI_MODEL`).
- **Local experimentation**: LM Studio, running a local GGUF model (for prompt and analysis experiments outside the automated pipeline).

LM Studio and the local model were used for manual exploration, prompt design, and analysis experiments. The core pipeline in this repo can run without LM Studio; LM Studio is only needed if you want to reproduce the local experimentation setup.

---

## Quick Start

```bash
git clone https://github.com/Skoyer/sa_locals_rag.git
cd sa_locals_rag

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

cp .env.example .env   # then edit .env with your Locals + OpenAI settings

# Run the full pipeline
python run_full_pipeline.py
```

After the first run you should see:

- `playlist_archive.db` — SQLite database with videos, transcripts, and analysis.
- `data/` — downloaded videos and transcript files.
- `web/` — static HTML output.

For a more detailed walkthrough, see `docs/getting-started.md`.

---

## Project Status

This is currently a focused proof‑of‑concept built around Scott Adams’ Locals.com content. The architecture is being refactored to support additional sources (for example YouTube playlists and other creators) in the future.

---

## Documentation

More detailed documentation lives in the `docs/` folder:

- [Architecture](docs/architecture.md)
- [Getting Started](docs/getting-started.md)
- [Pipeline](docs/pipeline.md)
- [Database](docs/database.md)
- [CLI Reference](docs/cli-reference.md)
- [Web Interface](docs/web-interface.md)
- [Roadmap](docs/roadmap.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](docs/contributing.md)

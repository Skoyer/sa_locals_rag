# Getting Started

This guide walks you through setting up SA Locals RAG from scratch and running your first full pipeline.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Tested on 3.11 and 3.12 |
| ffmpeg | Must be on `PATH`; used for HLS download and audio extraction |
| Git | For cloning the repo |
| OpenAI API key | Required for LLM analysis stage; Whisper can run locally |
| Locals.com account | With access to the target playlist/community |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Skoyer/sa_locals_rag.git
cd sa_locals_rag
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browser

```bash
playwright install chromium
```

### 5. Install ffmpeg

- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to `PATH`

---

## Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Then edit `.env`:

```dotenv
# Locals.com credentials (used for automatic cookie login)
LOCALS_EMAIL=your@email.com
LOCALS_PASSWORD=yourpassword

# Target playlist URL to scrape
LOCALS_PLAYLIST_URL=https://scottadams.locals.com/feed?playlist=XXXXX

# OpenAI API key for LLM analysis
OPENAI_API_KEY=sk-...

# Optional: Whisper model size (tiny, base, small, medium, large)
WHISPER_MODEL=base
```

See [configuration.md](configuration.md) for a full reference of all variables.

---

## First Run

### Option A: Run the entire pipeline in one command

```bash
python run_full_pipeline.py
```

This will:
1. Log in to Locals.com and save cookies
2. Scrape the playlist for video URLs
3. Download all videos
4. Extract audio and run Whisper transcription
5. Run LLM analysis on transcripts
6. Generate the static web playlist

### Option B: Run stages individually

```bash
# Stage 1: Download videos
python main.py

# Stage 2: Transcribe downloaded videos
python run_transcription.py

# Stage 3: Run LLM analysis pipeline
python -m pipeline.llm_pipeline

# Stage 4: Generate static web page
python -m web.generate  # (if applicable)
```

---

## Verifying Setup

After the first run, check:

```bash
# Check download progress
python check_progress.py

# Check for any download issues
python check_downloads.py

# Export data to CSV for inspection
python export_csv.py
```

You should see a `playlist_archive.db` SQLite file and a `data/` directory with downloaded videos and transcripts.

---

## Directory Structure After Setup

```
sa_locals_rag/
├── .env                    # Your local secrets (gitignored)
├── playlist_archive.db     # SQLite database
├── playlist_archive.csv    # Exported CSV snapshot
├── data/
│   ├── videos/             # Downloaded MP4/MKV files
│   └── transcripts/        # Whisper transcript .txt files
├── wordclouds/             # Generated word cloud images
└── web/                    # Static HTML output
```

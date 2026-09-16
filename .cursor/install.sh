#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for SA Locals RAG.
# Prepares the Python pipeline (venv + Whisper/PyTorch + Playwright) and the
# two Vite/React frontends (topic-browser, web2).
set -euo pipefail

# Resolve repo root (this script lives in .cursor/).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- System packages not present in the base image ---
# python3.12-venv is required to create the virtualenv; ffmpeg/ffprobe are
# required by the transcription and help-indexer pipelines.
if ! dpkg -s python3.12-venv >/dev/null 2>&1 || ! command -v ffmpeg >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends \
    python3.12-venv python3-pip python3-dev ffmpeg
fi

# --- Python environment ---
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
# Chromium is used by the Locals.com login/fetch flow (Playwright).
python -m playwright install --with-deps chromium

# --- Frontend dependencies ---
(cd topic-browser && npm install)
(cd web2 && npm install)

# --- Word cloud images for the topic-browser dev server ---
# lessons.json references /wordclouds/<...>.png; link the repo image folders
# into topic-browser/public so Vite serves them during dev.
wc_pub="topic-browser/public/wordclouds"
mkdir -p "$wc_pub"
ln -sfn ../../../wordclouds/per_video "$wc_pub/per_video"
ln -sfn ../../../wordclouds/clusters "$wc_pub/clusters"
ln -sfn ../../../wordclouds/topics "$wc_pub/topics"
ln -sfn ../../../wordclouds/master_wordcloud.png "$wc_pub/master_wordcloud.png"

echo "SA Locals RAG environment ready."

"""Configuration from environment variables (and optional .env file)."""
import os

from dotenv import load_dotenv

# Load .env from project root so PLAYLIST_URL, LOCALS_EMAIL, etc. can live in one file (gitignored)
load_dotenv()

PLAYLIST_URL: str | None = os.environ.get("PLAYLIST_URL")
OUTPUT_DIR: str = os.environ.get("OUTPUT_DIR", "./downloads")
DB_PATH: str = os.environ.get("DB_PATH", "./playlist_archive.db")

# Scheduler cadence
RUN_EVERY_MINUTES: int = int(os.environ.get("RUN_EVERY_MINUTES", "5"))

# Locals.com subscriber login (for PLAYLIST_URLs on locals.com)
LOCALS_EMAIL: str | None = os.environ.get("LOCALS_EMAIL")
LOCALS_PASSWORD: str | None = os.environ.get("LOCALS_PASSWORD")
LOCALS_COOKIES_PATH: str = os.environ.get("LOCALS_COOKIES_PATH", "./locals_cookies.txt")

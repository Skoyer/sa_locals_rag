# scripts/generate_short_titles.py
# Run once to add short_title to each lesson in lessons.json
# Uses OpenAI-compatible API (works with LM Studio local server too)

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / "topic-browser" / "public" / "lessons.json"

client = OpenAI(
    base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:1234/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "lm-studio"),
)

with LESSONS.open(encoding="utf-8") as f:
    lessons = json.load(f)

for lesson in lessons:
    if lesson.get("short_title"):
        continue  # skip already processed

    summary = lesson.get("summary_text") or lesson.get("summary", "")

    prompt = f"""Given this lesson title: "{lesson['title']}"
And this summary: "{summary}"

Return a SHORT_TITLE: a clear 3-6 word title describing the core idea.
No prefix like "Micro Lesson", "Episode", or person names.
Return only the short title."""

    resp = client.chat.completions.create(
        model="local-model",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=30,
    )
    lesson["short_title"] = resp.choices[0].message.content.strip()
    print(f"✓ {lesson['short_title']}  ←  {lesson['title']}")

with LESSONS.open("w", encoding="utf-8") as f:
    json.dump(lessons, f, indent=2)

print("Done. lessons.json updated with short_title fields.")

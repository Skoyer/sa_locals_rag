Topic Browser Redesign Spec
Core UX Problems Being Solved
The current layout has four critical UX failures:
​

No entry point — users land on a blank grid with no guidance on how to start.

"Learning Paths" tab is a dead end — you can't create a path without first going back to Videos, filtering, then returning to Learning Paths. The flow is invisible.

Titles are noisy — "A Micro Lesson on…" and "Episode 975 Scott Adams" repeat on every card; the actual topic is buried.

Layout hierarchy is wrong — search is the dominant visual element but it's the least important starting point for a new user; interest-based discovery should come first.

1. Landing Page: Make Learning Paths the Default
Change the default tab from "Videos" to "Learning Paths".

The first thing a new user sees should answer: "What can I learn here and where do I start?"

Landing page layout
text
┌─────────────────────────────────────────────────┐
│  Topic Browser                    [Sign in]      │
│  Bite-sized lessons from Scott Adams' library    │
├─────────────────────────────────────────────────┤
│                                                 │
│   What do you want to get better at?            │
│                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │🧠 Thinking│ │💬 Persuasion│ │⚡ Energy  │      │
│  └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │🎨 Creativity││💼 Career  │ │❤️ Health  │      │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                 │
│   ─── or browse all videos ───                  │
├─────────────────────────────────────────────────┤
│  Featured Learning Paths                        │
│  ┌─────────────┐ ┌─────────────┐               │
│  │ Persuasion  │ │  Clear      │               │
│  │ Starter     │ │  Thinking   │               │
│  │ 8 lessons   │ │  12 lessons │               │
│  │ [Start →]   │ │ [Start →]   │               │
│  └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────┘
Interest tiles drive discovery; clicking one filters and takes the user straight into a ready-made path.

"Browse all videos" is a secondary action — not the entry point.

Featured paths are shown below the interest grid so users can also start from a curated recommendation.

2. Video Title Cleanup
The problem
Every card says "A Micro Lesson on…" or "Episode 975 Scott Adams". That is metadata, not a title.

The fix: add a short_title field
Run a one-time LLM pass (LM Studio or OpenAI batch) over lessons.json to generate a short_title per video:

Prompt template per video:

text
Given this lesson title: "{title}"
And this summary: "{summary}"

Return a SHORT_TITLE: a clear 3-6 word title that describes the core idea, 
with no prefix like "Micro Lesson", "Episode", or person names.
Example: "The Power of Praise" not "A Micro Lesson on the power of praise"
Return only the short title, nothing else.
Card display after fix:

text
┌──────────────────────────────────┐
│  The Power of Praise   [beginner]│
│                                  │
│  Praise and compliments are free │
│  but highly valuable…            │
│                                  │
│  persuasion  self-programming    │
│  Cluster: Social Interactions    │
│                                  │
│  ✓ Watched  [Add to path]        │
│  ─────────────────────────────── │
│  A Micro Lesson on the power of  │  ← small muted text
│  praise (Episode 940)            │
└──────────────────────────────────┘
Python script to generate short_titles
Add this to web/summary_page.py or as a standalone scripts/generate_short_titles.py:

python
# scripts/generate_short_titles.py
# Run once to add short_title to each lesson in lessons.json
# Uses OpenAI-compatible API (works with LM Studio local server too)

import json
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",  # swap for OpenAI if preferred
    api_key="lm-studio"
)

with open("topic-browser/public/lessons.json") as f:
    lessons = json.load(f)

for lesson in lessons:
    if lesson.get("short_title"):
        continue  # skip already processed

    prompt = f"""Given this lesson title: "{lesson['title']}"
And this summary: "{lesson.get('summary', '')}"

Return a SHORT_TITLE: a clear 3-6 word title describing the core idea.
No prefix like "Micro Lesson", "Episode", or person names.
Return only the short title."""

    resp = client.chat.completions.create(
        model="local-model",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=30
    )
    lesson["short_title"] = resp.choices[0].message.content.strip()
    print(f"✓ {lesson['short_title']}  ←  {lesson['title']}")

with open("topic-browser/public/lessons.json", "w") as f:
    json.dump(lessons, f, indent=2)

print("Done. lessons.json updated with short_title fields.")
3. Interest Tile → Learning Path Flow
Replace the current "go to Videos, filter, go back to Learning Paths" workflow with a direct guided flow:

Step 1: User clicks an interest tile (e.g., "Persuasion")
App filters videos to the persuasion topic bucket.

Shows a modal or inline panel:

text
┌──────────────────────────────────────────┐
│  🎯 Persuasion — 14 lessons found        │
│                                          │
│  Start with the recommended path         │
│  ┌──────────────────────────────────┐   │
│  │ Persuasion Starter (8 lessons)   │   │
│  │ Covers: framing, social proof,   │   │
│  │ emotional reasoning              │   │
│  │          [Start this path →]     │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ── or ──                                │
│                                          │
│  [Browse all 14 Persuasion videos]       │
│  [Save filtered set as my own path]      │
└──────────────────────────────────────────┘
Step 2: Path detail view
When a path is started, the Videos tab updates to show only those videos in order, with a progress bar at the top:

text
┌───────────────────────────────────────────────────┐
│  Path: Persuasion Starter     ████░░░░  2 of 8    │
│  [← Back to paths]  [Mark all watched]            │
└───────────────────────────────────────────────────┘
This gives users clear visual feedback that they are "in" a path.

4. Recommended Featured Paths
Based on the topics in your data, here are 6 curated starter paths to hardcode in featured_learning_paths:

Path Title	Topic buckets	Approx videos
Persuasion & Influence	persuasion, communication, compliments	10–14
Clear Thinking	cognitive_bias, critical_thinking, self_programming	12–15
Career & Creativity	career, creativity, personal_brand	8–10
Health & Energy	health, diet, energy_management	6–8
Social Confidence	social_skills, confidence, accusation	6–8
Emotional Mastery	emotional_intelligence, mindfulness, stress	8–10
These map directly to your existing topic_buckets in lessons.json.
​

5. Full Layout Redesign Summary
Element	Current	Redesigned
Element	Current	Redesigned
Default tab	Videos	Learning Paths
Entry point	Search bar	Interest tiles
Card title	"A Micro Lesson on…"	Short title (3–6 words)
Original title	Hidden	Small muted subtext on card
Path creation	Filter → go to tab → button	Click tile → modal → one click
Progress visibility	None	Progress bar in path view
Topics sidebar	Always visible	Collapsed by default on landing; expands in Browse mode

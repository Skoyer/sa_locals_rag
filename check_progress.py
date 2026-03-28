import sqlite3

conn = sqlite3.connect('help_videos.db')

rows = conn.execute("""
    SELECT v.title, v.filename, COUNT(ts.id) AS segments
    FROM videos v
    LEFT JOIN transcript_segments ts ON ts.video_id = v.id
    GROUP BY v.id
    ORDER BY v.id DESC
    LIMIT 20
""").fetchall()

print(f"{'Title':<50} {'Segments':>8}")
print("-" * 60)
for title, filename, segments in rows:
    label = (title or filename or "unknown")[:48]
    print(f"{label:<50} {segments:>8}")

conn.close()



conn = sqlite3.connect('help_videos.db')

total_videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
total_segments = conn.execute("SELECT COUNT(*) FROM transcript_segments").fetchone()[0]

print(f"Videos transcribed so far: {total_videos} / 260")
print(f"Total transcript segments indexed: {total_segments}")
conn.close()

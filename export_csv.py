import sqlite3
import csv

db_path = "playlist_archive.db"
table = "videos"
out_csv = "playlist_archive.csv"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute(f"SELECT * FROM {table}")
rows = cur.fetchall()
headers = [d[0] for d in cur.description]

with open(out_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(rows)

conn.close()

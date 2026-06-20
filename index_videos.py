import json
import os
import sqlite3
from youtube_transcript_api import YouTubeTranscriptApi

DB_PATH = os.path.join("db", "app.db")
SEED_PATH = "seed_videos.json"

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  youtube_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS captions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id INTEGER NOT NULL,
  start REAL NOT NULL,
  duration REAL NOT NULL,
  text TEXT NOT NULL,
  FOREIGN KEY(video_id) REFERENCES videos(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS captions_fts USING fts5(
  text,
  caption_id UNINDEXED,
  video_id UNINDEXED,
  start UNINDEXED,
  content=''
);
"""

def init_db(conn):
    conn.executescript(SCHEMA_SQL)
    conn.commit()

def upsert_video(conn, youtube_id, title):
    conn.execute(
        "INSERT OR IGNORE INTO videos (youtube_id, title) VALUES (?, ?)",
        (youtube_id, title)
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM videos WHERE youtube_id = ?",
        (youtube_id,)
    ).fetchone()
    return int(row[0])

def already_indexed(conn, video_id):
    row = conn.execute(
        "SELECT 1 FROM captions WHERE video_id = ? LIMIT 1",
        (video_id,)
    ).fetchone()
    return row is not None

def fetch_lines(api, youtube_id):
    # Try Korean first, then English, then “anything”
    for langs in (["ko"], ["ko", "en"], ["en"], None):
        try:
            if langs is None:
                return api.fetch(youtube_id)
            return api.fetch(youtube_id, languages=langs)
        except Exception:
            pass
    return None

def line_to_fields(line):
    """
    Supports:
    - dict format: {"text": "...", "start": 1.2, "duration": 3.4}
    - object format (FetchedTranscriptSnippet): line.text, line.start, line.duration
    """
    if isinstance(line, dict):
        text = (line.get("text") or "").strip()
        start = float(line.get("start", 0.0))
        duration = float(line.get("duration", 0.0))
        return text, start, duration

    # Object/snippet format
    text = (getattr(line, "text", "") or "").strip()
    start = float(getattr(line, "start", 0.0) or 0.0)
    duration = float(getattr(line, "duration", 0.0) or 0.0)
    return text, start, duration

def index_video(conn, api, youtube_id, title):
    print(f"Indexing: {title} ({youtube_id})")

    video_id = upsert_video(conn, youtube_id, title)

    if already_indexed(conn, video_id):
        print("  SKIP: already indexed")
        return

    lines = fetch_lines(api, youtube_id)
    if not lines:
        print("  FAIL: no transcript available (or restricted/disabled)")
        return

    inserted = 0
    for line in lines:
        text, start, duration = line_to_fields(line)
        if not text:
            continue

        cur = conn.execute(
            "INSERT INTO captions (video_id, start, duration, text) VALUES (?, ?, ?, ?)",
            (video_id, start, duration, text)
        )
        caption_id = cur.lastrowid

        conn.execute(
            "INSERT INTO captions_fts (text, caption_id, video_id, start) VALUES (?, ?, ?, ?)",
            (text, caption_id, video_id, start)
        )

        inserted += 1

    conn.commit()
    print(f"  OK: inserted {inserted} lines")

def main():
    os.makedirs("db", exist_ok=True)

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        videos = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    api = YouTubeTranscriptApi()  # instance-based API (has .fetch)

    for v in videos:
        index_video(conn, api, v["youtube_id"], v.get("title", v["youtube_id"]))

    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
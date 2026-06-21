import json
import os
import sqlite3
from youtube_transcript_api import YouTubeTranscriptApi
import time
import requests

DB_PATH = os.path.join("db", "app.db")

VIDEO_FILES = [
    ("seed_videos.json", "real"),
    ("ttmik_videos_filtered.json", "ttmik"),
]

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  youtube_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  source TEXT DEFAULT 'real'
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

    # Migration for older databases that do not have source yet
    columns = conn.execute("PRAGMA table_info(videos)").fetchall()
    column_names = [col[1] for col in columns]

    if "source" not in column_names:
        conn.execute("ALTER TABLE videos ADD COLUMN source TEXT DEFAULT 'real'")
        conn.commit()

def upsert_video(conn, youtube_id, title, source):
    conn.execute(
        """
        INSERT INTO videos (youtube_id, title, source)
        VALUES (?, ?, ?)
        ON CONFLICT(youtube_id) DO UPDATE SET
            title = excluded.title,
            source = excluded.source
        """,
        (youtube_id, title, source)
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

def needs_indexing(conn, youtube_id):
    row = conn.execute("""
        SELECT c.id
        FROM videos v
        JOIN captions c ON c.video_id = v.id
        WHERE v.youtube_id = ?
        LIMIT 1
    """, (youtube_id,)).fetchone()

    return row is None

def fetch_lines(api, youtube_id):
    for langs in (["ko"], ["ko", "en"], ["en"], None):
        try:
            if langs is None:
                return api.fetch(youtube_id)
            return api.fetch(youtube_id, languages=langs)
        except Exception as e:
            print(f"  Transcript error with {langs}: {type(e).__name__}")
    return None

def line_to_fields(line):
    if isinstance(line, dict):
        text = (line.get("text") or "").strip()
        start = float(line.get("start", 0.0))
        duration = float(line.get("duration", 0.0))
        return text, start, duration

    text = (getattr(line, "text", "") or "").strip()
    start = float(getattr(line, "start", 0.0) or 0.0)
    duration = float(getattr(line, "duration", 0.0) or 0.0)

    return text, start, duration

def index_video(conn, api, youtube_id, title, source):
    print(f"Indexing [{source}]: {title} ({youtube_id})")

    video_id = upsert_video(conn, youtube_id, title, source)

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

def load_video_files():
    videos = []

    for path, default_source in VIDEO_FILES:
        if not os.path.exists(path):
            print(f"Skipping missing file: {path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for v in data:
            youtube_id = v.get("youtube_id")
            title = v.get("title", youtube_id)
            source = v.get("source", default_source)

            if not youtube_id:
                continue

            videos.append({
                "youtube_id": youtube_id,
                "title": title,
                "source": source
            })

    return videos

def main():
    os.makedirs("db", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    session = requests.Session()

    original_request = session.request

    def request_with_timeout(method, url, **kwargs):
        kwargs.setdefault("timeout", 15)
        return original_request(method, url, **kwargs)
    

    

    session.request = request_with_timeout

    api = YouTubeTranscriptApi(http_client=session)

    videos = load_video_files()

    videos = [
        v for v in videos
        if needs_indexing(conn, v["youtube_id"])
    ]

    print(f"Need to index: {len(videos)} videos")

    for v in videos:
        index_video(
            conn,
            api,
            v["youtube_id"],
            v["title"],
            v["source"]
        )

        time.sleep(6)
        

    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
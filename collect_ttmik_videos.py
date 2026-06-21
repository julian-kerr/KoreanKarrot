import json
import yt_dlp

CHANNEL_URL = "https://www.youtube.com/@talktomeinkorean/videos"

ydl_opts = {
    "extract_flat": True,
    "skip_download": True,
    "quiet": True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(CHANNEL_URL, download=False)

videos = []

for entry in info.get("entries", []):
    title = entry.get("title", "")
    video_id = entry.get("id", "")

    if not title or not video_id:
        continue

    videos.append({
        "title": title,
        "youtube_id": video_id,
        "source": "ttmik"
    })

with open("ttmik_videos.json", "w", encoding="utf-8") as f:
    json.dump(videos, f, ensure_ascii=False, indent=2)

print(f"Saved {len(videos)} TTMIK videos to ttmik_videos.json")
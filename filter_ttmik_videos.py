import json

GOOD_WORDS = [
    "phrase", "phrases",
    "grammar",
    "conversation", "conversations",
    "listening",
    "vocabulary", "vocab",
    "sentence", "sentences",
    "verb", "verbs",
    "adjective", "adjectives",
    "expression", "expressions",
    "pronunciation",
    "learn korean",
    "korean lesson",
    "korean words",
    "how to say",
    "beginner",
    "intermediate",
    "level"
]

BAD_WORDS = [
    "movie",
    "marvel",
    "bts",
    "k-pop",
    "kpop",
    "book",
    "books",
    "look inside",
    "vlog",
    "shorts",
    "live",
    "livestream",
    "podcast",
    "announcement",
    "update",
    "emotional",
    "viral"
]

with open("ttmik_videos.json", "r", encoding="utf-8") as f:
    videos = json.load(f)

filtered = []

for video in videos:
    title = video["title"]
    lower = title.lower()

    if any(bad in lower for bad in BAD_WORDS):
        continue

    if any(good in lower for good in GOOD_WORDS):
        filtered.append(video)

with open("ttmik_videos_filtered.json", "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print(f"Original: {len(videos)}")
print(f"Filtered: {len(filtered)}")

print("\nFirst 30 filtered:")
for v in filtered[:30]:
    print("-", v["title"])
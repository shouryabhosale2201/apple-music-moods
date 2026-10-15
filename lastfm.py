"""Step 2: fetch mood signals (tags) for every song from Last.fm. Results are cached."""
import json
import re
import time

import requests

from config import (DATA_DIR, LASTFM_API_KEY, LASTFM_DELAY_SEC,
                    LASTFM_MAX_TAGS, LASTFM_MIN_TAG_COUNT)

API_URL = "https://ws.audioscrobbler.com/2.0/"
TAGS_FILE = DATA_DIR / "tags.json"
ARTIST_TAGS_FILE = DATA_DIR / "artist_tags.json"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "apple-music-moods/1.0"
_last_call = 0.0

TITLE_NOISE = [
    r"\s*[\(\[](feat\.?|ft\.?|featuring|with)\s[^\)\]]*[\)\]]",
    r"\s*[\(\[][^\)\]]*(remaster|version|edit|live|mono|stereo|deluxe|bonus|from\s)[^\)\]]*[\)\]]",
    r"\s+-\s+.*(remaster|version|edit|live|mono|stereo).*$",
]


def clean_title(title):
    t = title
    for pat in TITLE_NOISE:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    return t.strip() or title


def primary_artist(artist):
    parts = re.split(r"\s*(?:,|&|\bfeat\.?\s|\bft\.?\s|\sx\s)\s*", artist, flags=re.IGNORECASE)
    return parts[0].strip() or artist


def _call(params, retries=3):
    global _last_call
    params = {**params, "api_key": LASTFM_API_KEY, "format": "json", "autocorrect": 1}
    for attempt in range(retries):
        wait = LASTFM_DELAY_SEC - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            data = SESSION.get(API_URL, params=params, timeout=15).json()
        except (requests.RequestException, ValueError):
            time.sleep(2 * (attempt + 1))
            continue
        if "error" in data:
            if data["error"] in (11, 16, 29):  # service down / temporary / rate limited
                time.sleep(5 * (attempt + 1))
                continue
            if data["error"] in (10, 26):
                raise SystemExit("Invalid Last.fm API key. Check LASTFM_API_KEY.")
            return None  # e.g. 6 = not found
        return data
    return None


def _parse_tags(data):
    if not data:
        return []
    tags = data.get("toptags", {}).get("tag", [])
    if isinstance(tags, dict):
        tags = [tags]
    out = []
    for t in tags[:LASTFM_MAX_TAGS]:
        try:
            count = int(t.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        if count >= LASTFM_MIN_TAG_COUNT and t.get("name"):
            out.append([t["name"].strip().lower(), count])
    return out


def track_tags(artist, title):
    attempts = [(artist, title), (artist, clean_title(title)),
                (primary_artist(artist), clean_title(title))]
    seen = set()
    for a, t in attempts:
        if (a, t) in seen or not a or not t:
            continue
        seen.add((a, t))
        tags = _parse_tags(_call({"method": "track.getTopTags", "artist": a, "track": t}))
        if tags:
            return tags
    return []


def artist_tags(artist):
    return _parse_tags(_call({"method": "artist.getTopTags", "artist": artist}))


def _load(path):
    return json.loads(path.read_text()) if path.exists() else {}


def fetch_all(songs, refresh=False):
    if not LASTFM_API_KEY:
        raise SystemExit("Set LASTFM_API_KEY first (see README).")
    cache = {} if refresh else _load(TAGS_FILE)
    artist_cache = {} if refresh else _load(ARTIST_TAGS_FILE)

    todo = [s for s in songs if s["id"] not in cache]
    print(f"{len(songs) - len(todo)} songs cached, fetching tags for {len(todo)}...")

    for i, s in enumerate(todo, 1):
        artist = s.get("artist") or ""
        main_artist = primary_artist(artist) if artist else ""
        if main_artist and main_artist not in artist_cache:
            artist_cache[main_artist] = artist_tags(main_artist)
        cache[s["id"]] = {
            "track_tags": track_tags(artist, s["title"]) if artist else [],
            "artist_tags": artist_cache.get(main_artist, []),
        }
        if i % 25 == 0 or i == len(todo):
            TAGS_FILE.write_text(json.dumps(cache, ensure_ascii=False))
            ARTIST_TAGS_FILE.write_text(json.dumps(artist_cache, ensure_ascii=False))
            print(f"  {i}/{len(todo)}  last: {artist} - {s['title']}")

    found = sum(1 for s in songs if cache.get(s["id"], {}).get("track_tags"))
    print(f"Done. {found}/{len(songs)} songs have track-level tags.")
    return cache


def load_tags():
    return _load(TAGS_FILE)

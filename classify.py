"""Step 3: classify each song into mood playlists.

Order of precedence:
  1. overrides.json (your manual corrections)
  2. rule-based scoring from Last.fm tags + genre
  3. LLM for songs the rules are unsure about (optional)
"""
import csv
import json
from collections import Counter, defaultdict

import llm
from config import (ARTIST_TAG_WEIGHT, BASE_DIR, CONFLICTS, DATA_DIR, LLM_BATCH_SIZE,
                    LLM_DECIDES_ALL, MAX_PLAYLISTS_PER_SONG, MIN_SCORE,
                    PLAYLISTS, SECONDARY_RATIO)

CLASSIFIED_FILE = DATA_DIR / "classified.json"
REPORT_FILE = DATA_DIR / "report.csv"
LLM_CACHE_FILE = DATA_DIR / "llm_cache.json"
OVERRIDES_FILE = BASE_DIR / "overrides.json"

CONFLICT_SET = {frozenset(p) for p in CONFLICTS}


def song_key(song):
    return f"{(song.get('artist') or '').lower().strip()}|{song['title'].lower().strip()}"


def normalize_tag(tag):
    t = tag.lower().strip().replace("_", " ")
    return {"lo fi": "lo-fi", "hip hop": "hip-hop", "feel-good": "feel good"}.get(t, t)


# ---------- rules ----------

def score_song(song, tag_entry):
    scores = defaultdict(float)
    track = tag_entry.get("track_tags", [])
    signals = [(n, c) for n, c in track]
    if len(track) < 3:  # sparse track tags -> lean on artist tags
        signals += [(n, c * ARTIST_TAG_WEIGHT) for n, c in tag_entry.get("artist_tags", [])]

    for name, count in signals:
        tag = normalize_tag(name)
        for pl, spec in PLAYLISTS.items():
            w = spec["tags"].get(tag)
            if w:
                scores[pl] += w * count / 100

    genre = (song.get("genre") or "").lower()
    for pl, spec in PLAYLISTS.items():
        for g, w in spec.get("genres", {}).items():
            if g in genre:
                scores[pl] += w
    return scores


def pick(scores):
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked or ranked[0][1] < MIN_SCORE:
        return []
    top_name, top_score = ranked[0]
    chosen = [top_name]
    for name, sc in ranked[1:]:
        if len(chosen) >= MAX_PLAYLISTS_PER_SONG:
            break
        if sc >= max(MIN_SCORE, top_score * SECONDARY_RATIO) and \
                not any(frozenset((name, c)) in CONFLICT_SET for c in chosen):
            chosen.append(name)
    return chosen


# ---------- LLM ----------

LLM_SYSTEM = """You sort songs into mood playlists.

Playlists:
{playlists}

For each song you get id, title, artist, album, genre, year and crowd-sourced tags (may be empty).
Use your knowledge of the song if you know it; otherwise infer from artist, genre, title and tags.
Assign 1 to {max_n} playlists per song, best fit first. Only use [] if you truly cannot tell.
Songs may be in any language (e.g. Tamil, Hindi, Korean, Spanish); judge the mood, not the language.

Respond with ONLY JSON, no markdown:
{{"results": [{{"id": "<id>", "playlists": ["<name>", ...]}}]}}"""


def _extract_json(text):
    text = text.strip().replace("```json", "").replace("```", "")
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def llm_classify(items, tags):
    """items: list of songs. Returns {song_id: [playlists]}"""
    cache = json.loads(LLM_CACHE_FILE.read_text()) if LLM_CACHE_FILE.exists() else {}
    todo = [s for s in items if s["id"] not in cache]
    if todo:
        print(f"Asking the LLM about {len(todo)} songs ({llm.describe()})...")
    system = LLM_SYSTEM.format(
        playlists="\n".join(f"- {n}: {p['description']}" for n, p in PLAYLISTS.items()),
        max_n=MAX_PLAYLISTS_PER_SONG,
    )
    valid = set(PLAYLISTS)
    size = llm.batch_size(LLM_BATCH_SIZE)

    for i in range(0, len(todo), size):
        batch = todo[i:i + size]
        payload = []
        for s in batch:
            t = tags.get(s["id"], {})
            top = [n for n, _ in (t.get("track_tags") or t.get("artist_tags") or [])][:8]
            payload.append({k: s.get(k) for k in ("id", "title", "artist", "album", "genre", "year")}
                           | {"tags": top})
        try:
            text = llm.complete(system, json.dumps(payload, ensure_ascii=False))
            for r in _extract_json(text).get("results", []):
                cache[str(r.get("id"))] = [p for p in r.get("playlists", []) if p in valid][:MAX_PLAYLISTS_PER_SONG]
        except llm.QuotaExhausted as e:  # no point sending more batches today
            print(f"  Stopping: {e}")
            break
        except (RuntimeError, ValueError, KeyError) as e:  # keep going; failed batch is retried next run
            print(f"  LLM batch failed ({e}); will retry on next run.")
            continue
        LLM_CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False))
        print(f"  {min(i + size, len(todo))}/{len(todo)}")
    # songs missing here are still pending (failed batch / quota), not "no answer"
    return {s["id"]: cache[s["id"]] for s in items if s["id"] in cache}


# ---------- overrides ----------

def load_overrides():
    if not OVERRIDES_FILE.exists():
        return {}, {}, set()
    o = json.loads(OVERRIDES_FILE.read_text())
    songs = {k.lower(): v for k, v in o.get("songs", {}).items()}
    artists = {k.lower(): v for k, v in o.get("artists", {}).items()}
    exclude = {k.lower() for k in o.get("exclude", [])}
    return songs, artists, exclude


# ---------- main ----------

def classify_all(songs, tags, use_llm=None, llm_all=False):
    use_llm = llm.is_enabled() if use_llm is None else use_llm
    if use_llm and LLM_DECIDES_ALL:
        llm_all = True
    if llm_all and not use_llm:
        llm_all = False
    song_ov, artist_ov, exclude = load_overrides()

    results, unsure = {}, []
    for s in songs:
        key = song_key(s)
        artist = (s.get("artist") or "").lower()
        if key in exclude:
            results[s["id"]] = ([], "excluded", {})
        elif key in song_ov:
            results[s["id"]] = (song_ov[key], "override", {})
        elif artist in artist_ov:
            results[s["id"]] = (artist_ov[artist], "artist-override", {})
        else:
            scores = score_song(s, tags.get(s["id"], {}))
            chosen = [] if llm_all else pick(scores)
            results[s["id"]] = (chosen, "rules" if chosen else "none", scores)
            if not chosen:
                unsure.append(s)

    if unsure and use_llm:
        answers = llm_classify(unsure, tags)
        pending = len(unsure) - len(answers)
        if pending:
            raise SystemExit(
                f"\n{pending} of {len(unsure)} songs still need the LLM, so no report was written.\n"
                f"Progress is cached in {LLM_CACHE_FILE.name}; run `python main.py classify` again later "
                f"to continue, or use --no-llm to classify with rules only.")
        for sid, pls in answers.items():
            scores = results[sid][2]
            if pls:
                results[sid] = (pls, "llm", scores)
            elif pick(scores):  # LLM had no answer -> fall back to the rules
                results[sid] = (pick(scores), "rules-fallback", scores)
    elif unsure:
        print(f"{len(unsure)} songs unclassified (set up a free LLM provider to handle them, see README).")

    assignments = {sid: pls for sid, (pls, _, _) in results.items() if pls}
    CLASSIFIED_FILE.write_text(json.dumps(assignments, indent=2))
    _write_report(songs, tags, results)

    counts = Counter(p for pls in assignments.values() for p in pls)
    sources = Counter(src for _, src, _ in results.values())
    print("\nPlaylist sizes:")
    for name in PLAYLISTS:
        print(f"  {name:<12} {counts.get(name, 0)}")
    print(f"\nHow songs were decided: {dict(sources)}")
    print(f"Review: {REPORT_FILE}")
    return assignments


def _write_report(songs, tags, results):
    with REPORT_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["artist", "title", "genre", "playlists", "source", "top_scores", "top_tags", "override_key"])
        for s in songs:
            pls, src, scores = results[s["id"]]
            t = tags.get(s["id"], {})
            top_tags = ", ".join(n for n, _ in (t.get("track_tags") or t.get("artist_tags") or [])[:6])
            top_scores = ", ".join(f"{k}:{v:.1f}" for k, v in sorted(scores.items(), key=lambda kv: -kv[1])[:3])
            w.writerow([s.get("artist"), s["title"], s.get("genre"), " + ".join(pls), src,
                        top_scores, top_tags, song_key(s)])


def load_classified():
    if not CLASSIFIED_FILE.exists():
        raise SystemExit("Nothing classified yet. Run: python main.py classify")
    return json.loads(CLASSIFIED_FILE.read_text())

"""
Central configuration. Edit PLAYLISTS to add, remove or tune moods.

Each playlist has:
  description : used by the LLM to understand the mood
  tags        : Last.fm tag -> weight (how strongly that tag signals this mood)
  genres      : substring of Apple Music genre -> weight (weaker signal)
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Every playlist this tool creates starts with this prefix.
# The tool ONLY ever touches playlists with this prefix.
PLAYLIST_PREFIX = "Mood · "

PLAYLISTS = {
    "Chill": {
        "description": "Calm, relaxed, laid-back songs. Lo-fi, acoustic, soft, mellow, easy listening.",
        "tags": {
            "chill": 3, "chillout": 3, "chill out": 3, "chill vibes": 3, "relaxing": 3,
            "relax": 3, "mellow": 2.5, "calm": 2.5, "lo-fi": 3, "lofi": 3, "chillhop": 3,
            "downtempo": 2.5, "laid back": 2.5, "laid-back": 2.5, "easy listening": 2,
            "peaceful": 2, "soft": 1.5, "acoustic": 1.5, "smooth": 1.5, "ambient": 1.5,
            "dreamy": 1.5, "soothing": 2.5, "chilled": 3,
        },
        "genres": {"easy listening": 1.0, "ambient": 0.8, "lo-fi": 1.2},
    },
    "Hard": {
        "description": "Aggressive, heavy, intense songs. Hard rock, metal, trap, drill, phonk, rage.",
        "tags": {
            "aggressive": 3, "heavy": 2.5, "hard rock": 2.5, "metal": 2.5, "heavy metal": 2.5,
            "metalcore": 3, "nu metal": 3, "hardcore": 2.5, "trap": 1, "drill": 2.5, "rage": 2.5,
            "intense": 1.5, "angry": 2.5, "dark trap": 2, "phonk": 2.5, "hard": 1, "brutal": 2.5,
            "hardstyle": 3, "dubstep": 2, "thrash metal": 3, "industrial": 2, "grime": 2,
            "punk": 1.5, "screamo": 2.5,
        },
        "genres": {"metal": 1.2, "hard rock": 1.2, "punk": 0.8},
    },
    "Workout": {
        "description": "High-energy, motivating songs with a driving beat, good for the gym or running.",
        "tags": {
            "workout": 4, "gym": 4, "running": 3, "pump up": 3.5, "motivation": 3,
            "motivational": 3, "energetic": 3, "high energy": 3, "hype": 3, "adrenaline": 3,
            "power": 2, "epic": 1.5, "edm": 1.5, "upbeat": 1.5, "anthem": 1.5, "energy": 2.5,
        },
        "genres": {"fitness": 1.5},
    },
    "Romantic": {
        "description": "Love songs, romantic, tender, sensual. Songs about being in love.",
        "tags": {
            "love": 3, "romantic": 4, "romance": 4, "love songs": 4, "love song": 4,
            "sensual": 2.5, "sexy": 2, "wedding": 2.5, "slow jams": 2.5, "tender": 2.5,
            "ballad": 1.5, "crush": 2, "beautiful": 1, "in love": 3.5,
        },
        "genres": {},
    },
    "Sad": {
        "description": "Sad, melancholic, heartbreak, emotional, lonely songs.",
        "tags": {
            "sad": 4, "sad songs": 4, "melancholy": 3.5, "melancholic": 3.5, "heartbreak": 4,
            "breakup": 3.5, "depressing": 3.5, "depressive": 3, "lonely": 3, "sorrow": 3,
            "crying": 3, "emotional": 2, "bittersweet": 2, "heartbroken": 4, "grief": 3,
        },
        "genres": {},
    },
    "Feel Good": {
        "description": "Happy, upbeat, positive, sunny songs that lift your mood.",
        "tags": {
            "happy": 3.5, "feel good": 4, "feelgood": 4, "upbeat": 2.5, "fun": 2.5,
            "cheerful": 3, "uplifting": 3, "positive": 3, "good vibes": 3, "joyful": 3,
            "optimistic": 3, "summer": 2, "sunny": 2.5, "catchy": 1.5, "good mood": 3.5,
        },
        "genres": {},
    },
    "Party": {
        "description": "Danceable party and club songs. Dance-pop, house, EDM, reggaeton, bangers.",
        "tags": {
            "party": 4, "dance": 3, "club": 3, "dancefloor": 3, "banger": 3, "dance pop": 2.5,
            "dance-pop": 2.5, "house": 2, "disco": 2, "edm": 2, "electro": 1.5,
            "reggaeton": 2.5, "dancehall": 2.5, "danceable": 3,
        },
        "genres": {"dance": 1.2, "house": 1.0, "reggaeton": 1.0, "dancehall": 1.0},
    },
    "Focus": {
        "description": "Instrumental or minimal-vocal music for studying and deep work. Classical, piano, soundtracks, post-rock, ambient.",
        "tags": {
            "instrumental": 3, "study": 4, "studying": 4, "focus": 4, "concentration": 4,
            "piano": 2, "classical": 2.5, "neoclassical": 3, "modern classical": 3,
            "post-rock": 2, "ambient": 2, "minimal": 2, "soundtrack": 2, "score": 2,
            "video game music": 2, "background": 2,
        },
        "genres": {"classical": 1.5, "soundtrack": 1.2, "instrumental": 1.5, "new age": 1.0},
    },
    "Late Night": {
        "description": "Moody, atmospheric, nocturnal songs for late nights and night drives. Alt R&B, synthwave, trip-hop.",
        "tags": {
            "late night": 3.5, "night": 2.5, "night drive": 4, "midnight": 3, "nocturnal": 3,
            "moody": 3, "atmospheric": 2.5, "dark": 2, "synthwave": 3, "alternative r&b": 3,
            "trip-hop": 3, "trip hop": 3, "noir": 2.5, "vaporwave": 2.5, "nighttime": 3,
        },
        "genres": {},
    },
}

# Pairs that should never both be assigned to one song.
CONFLICTS = [
    ("Sad", "Feel Good"),
    ("Chill", "Hard"),
    ("Chill", "Workout"),
    ("Focus", "Party"),
    ("Sad", "Party"),
]

# --- Classification tuning ---
MAX_PLAYLISTS_PER_SONG = 2   # a song can land in up to this many playlists
MIN_SCORE = 1.2              # below this, rules are "unsure" and the LLM decides
SECONDARY_RATIO = 0.6        # 2nd playlist must score >= 60% of the top one
ARTIST_TAG_WEIGHT = 0.5      # artist tags count half as much as track tags

# --- Last.fm ---
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "")
LASTFM_MIN_TAG_COUNT = 10    # ignore tags Last.fm rates below 10/100
LASTFM_MAX_TAGS = 15
LASTFM_DELAY_SEC = 0.22      # ~4-5 requests/sec, polite to Last.fm

# --- LLM (free providers: see llm.py) ---
LLM_BATCH_SIZE = 20   # default; providers in llm.py can override ("batch")
# True  = the LLM decides every song; Last.fm tags are passed to it as hints (most accurate)
# False = rules decide first, and the LLM only handles songs the rules are unsure about
LLM_DECIDES_ALL = True

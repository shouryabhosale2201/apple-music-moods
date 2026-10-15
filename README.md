# Apple Music Mood Playlists

I have 656 songs in Apple Music and couldn't just say "play something chill" from my
own library.

479 of those 656 songs are labelled **Hip-Hop/Rap**. A gym banger and a 2 AM heartbreak
track get the same genre tag. Shuffle gives you whiplash. Sorting 656 songs × 9 moods by
hand would take hours, and the work goes stale every time you add music. Nobody does it
twice.

So I built a tool that reads the whole library, works out the mood of every song, and
writes the playlists back into the Music app—where they sync straight to my iPhone.

**Chill · Hard · Workout · Romantic · Sad · Feel Good · Party · Focus · Late Night**

### How it works

```
export   ->  tags (Last.fm)  ->  classify (rules + LLM)  ->  build (Music app)
```

1. **Export** the library from the Music app via AppleScript (no Apple developer account,
   no Apple Music API—just JavaScript for Automation talking to the Mac's Music app).
2. **Tag** each song with crowd-sourced descriptors from Last.fm.
3. **Classify** mood with an LLM, using Last.fm tags as hints. The LLM recognises songs
   from title + artist in any language, so Bollywood and regional tracks aren't left out.
   A song can land in up to 2 playlists, and contradictions are blocked (nothing is both
   Sad and Party).
4. **Build** the playlists in Music. Only playlists starting with `Mood ·` are ever
   touched, so the rest of the library is safe.

### What broke along the way

- **Last.fm coverage was thin.** Tags existed for only 262 of 656 songs (40 %).
  Bollywood and regional music had almost nothing, so rules built on tags alone missed
  most of the library. The LLM fills the gap.
- **Free-tier quota is brutal.** Gemini's free tier gave 20 requests/day. Retry logic
  burned through the quota on retries, and the tool happily wrote a "finished" report
  with 80 % of songs unsorted. Fix: detect daily-quota errors and stop instead of
  retrying, cache every answer so the next run picks up where it left off, and write
  nothing until every song is sorted.
- **Retired models.** The Groq model I'd hardcoded got retired. Every batch returned a
  404, and the tool kept retrying. Lesson: a bad API key or model name won't fix itself
  on retry—stop right away.

### Result

655 of 656 songs sorted. The one it missed was literally a file named
`Mix by audio-joiner.com` 💀

```
Hard 229 · Party 215 · Workout 174 · Late Night 136 · Chill 131
Sad 115 · Romantic 110 · Feel Good 100 · Focus 20
```

Cost: **$0.** Last.fm and Groq are both free. Everything is cached, so next month only
new songs get looked up. Wrong pick? Put a fix in `overrides.json` and it survives every
rebuild.

## One-time setup (on your personal Mac)

1. **Turn on library sync.** In the Music app, go to Settings > General and enable
   **Sync Library**. Songs you've added from Apple Music then appear in the library,
   and the new playlists sync to your iPhone.

2. **Install Python 3.10+.** Run `python3 --version` to check. If needed, install from
   python.org or with `brew install python`.

3. **Set up the project:**
   ```bash
   cd apple-music-moods
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Get a Last.fm API key (free).** Log in at https://www.last.fm/api/account/create and
   create an "application" (any name; callback URL can be blank). Copy the API key.

5. **Set up a free LLM.** Choose one of these. The LLM is what makes the results good,
   since Last.fm alone misses most songs.

   - **Gemini** Go to https://aistudio.google.com/apikey, sign in with a
     personal Google account, and click **Create API key**. It's free and needs no card.
     It recognizes the most songs, including Tamil, Hindi and other regional music.
     Note that on the free tier, Google may use your inputs to improve its models. The
     only thing sent is song titles and artists.
   - **Groq (recommended):** Go to https://console.groq.com/keys. It's free, needs no card, and is
     very fast.
   - **Ollama (offline, unlimited):** Install it from https://ollama.com, then run
     `ollama pull qwen2.5:7b`. If your Mac has 16 GB of RAM or more, run
     `ollama pull qwen2.5:14b` and set `MOOD_LLM_MODEL=qwen2.5:14b`. Nothing leaves
     your Mac, but smaller models recognize fewer songs.

6. **Add your keys:**
   ```bash
   cp .env.example .env      # paste your Last.fm key, choose LLM_PROVIDER, add its key
   source .env
   ```

## Run it

```bash
source .venv/bin/activate && source .env

python main.py all --dry-run   # does everything except touch Music; check data/report.csv
python main.py all             # builds the playlists for real
```

The first time, macOS asks whether Terminal may control **Music**. Click **OK**. If you
missed the prompt, go to System Settings > Privacy & Security > Automation and enable it.

Or run the steps one at a time:

| Command | What it does |
|---|---|
| `python main.py export` | Reads your library into `data/library.json` |
| `python main.py tags` | Fetches Last.fm tags (cached; only new songs are fetched on reruns) |
| `python main.py classify` | Assigns moods, writes `data/report.csv` |
| `python main.py classify --no-llm` | Rules only |
| `python main.py classify --llm-all` | The LLM decides every song (the default, set by `LLM_DECIDES_ALL` in config.py) |
| `python main.py build --dry-run` | Shows playlist sizes |
| `python main.py build --only Chill` | Rebuilds one playlist |
| `python main.py clean` | Deletes every `Mood · ` playlist |

The tag step is the slow one: about 2 to 3 Last.fm calls per song at roughly 4 per
second, so a library of 1,000 songs takes about 10 minutes. After that, everything is
cached, and reruns take seconds plus however long the new songs need.

## Tuning

- **Playlists and moods:** Edit `PLAYLISTS` in `config.py`. Add a new entry, give it a
  description and some Last.fm tags, and it just works.
- **Wrong song placement:** Add it to `overrides.json`. The key is `artist|title` in
  lowercase, which you can copy from the `override_key` column in `report.csv`:
  ```json
  { "songs": {"the weeknd|blinding lights": ["Party", "Workout"]},
    "artists": {"lofi girl": ["Chill", "Focus"]},
    "exclude": ["some artist|song i hate"] }
  ```
- **Too many or too few songs per playlist:** Change `MIN_SCORE`, `SECONDARY_RATIO`
  and `MAX_PLAYLISTS_PER_SONG` in `config.py`.
- **Switching LLM providers:** Delete `data/llm_cache.json` so songs get re-asked.
- **After editing:** Run `python main.py classify && python main.py build`. This
  doesn't refetch tags.

## Keep it updated

Rerun `python main.py all` after adding music. To run it automatically every Sunday at
10am, use `crontab -e`:
```
0 10 * * 0 cd /path/to/apple-music-moods && source .venv/bin/activate && source .env && python main.py all >> data/cron.log 2>&1
```
For the cron job, also give **cron** Automation access to Music in System Settings.

## Good to know

- The tool only touches playlists whose names start with `Mood · `. Rebuilding clears
  and refills them, so manual edits to those playlists get overwritten. Use
  `overrides.json` for changes you want to keep.
- Removing a track from a playlist never removes it from your library.
- After a build, give iCloud a few minutes to sync the playlists to your phone.

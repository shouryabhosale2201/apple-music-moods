# Apple Music Mood Playlists

Reads your Apple Music library, figures out each song's mood, and builds playlists like
`Mood · Chill`, `Mood · Hard`, `Mood · Romantic` in the Music app. Runs on macOS.

```
export   ->  tags (Last.fm)  ->  classify (rules + optional LLM)  ->  build (Music app)
```

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

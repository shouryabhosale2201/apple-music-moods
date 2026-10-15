"""Step 1: read every song in your Apple Music library (via JXA / osascript)."""
import json
import subprocess

from config import DATA_DIR

LIBRARY_FILE = DATA_DIR / "library.json"

# JavaScript for Automation. Fetching each property for ALL tracks in one call
# is far faster than looping track by track.
JXA_EXPORT = r"""
function run() {
  const Music = Application('Music');
  const tracks = Music.libraryPlaylists[0].tracks;
  const n = tracks.length;
  const get = (prop) => {
    try { return tracks[prop](); } catch (e) { return new Array(n).fill(null); }
  };
  const ids = get('persistentID'), names = get('name'), artists = get('artist'),
        albumArtists = get('albumArtist'), albums = get('album'), genres = get('genre'),
        years = get('year'), durations = get('duration'), plays = get('playedCount'),
        kinds = get('mediaKind');
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      id: ids[i], title: names[i], artist: artists[i] || albumArtists[i] || '',
      album: albums[i], genre: genres[i], year: years[i],
      duration: durations[i], plays: plays[i], kind: kinds[i] ? String(kinds[i]) : null
    });
  }
  return JSON.stringify(out);
}
"""


def export_library():
    print("Reading Apple Music library (first run may ask for Automation permission)...")
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", JXA_EXPORT],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        err = result.stderr.strip()
        if "-1743" in err or "Not authorized" in err:
            raise SystemExit(
                "macOS blocked access to Music.\n"
                "Open System Settings > Privacy & Security > Automation, find Terminal "
                "(or your IDE) and enable 'Music'. Then run again."
            )
        raise SystemExit(f"osascript failed:\n{err}")

    tracks = json.loads(result.stdout)
    songs = [
        t for t in tracks
        if t.get("id") and t.get("title")
        and not (t.get("kind") and "video" in t["kind"].lower())
    ]
    LIBRARY_FILE.write_text(json.dumps(songs, indent=2, ensure_ascii=False))
    print(f"Exported {len(songs)} songs -> {LIBRARY_FILE}")
    return songs


def load_library():
    if not LIBRARY_FILE.exists():
        raise SystemExit("No library export found. Run: python main.py export")
    return json.loads(LIBRARY_FILE.read_text())


if __name__ == "__main__":
    export_library()

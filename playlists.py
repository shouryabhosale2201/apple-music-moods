"""Step 4: create or refresh the mood playlists in the Music app (AppleScript)."""
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from config import PLAYLIST_PREFIX, PLAYLISTS

# Clears the playlist (removes tracks from the PLAYLIST only, never from your library)
# and refills it with the given persistent IDs.
BUILD_SCRIPT = r'''
on run argv
    set plName to item 1 of argv
    set idFile to item 2 of argv
    set idList to paragraphs of (read (POSIX file idFile) as «class utf8»)
    set added to 0
    tell application "Music"
        with timeout of 3600 seconds
            if not (exists user playlist plName) then
                make new user playlist with properties {name:plName}
            end if
            set p to user playlist plName
            try
                delete every track of p
            end try
            repeat with pid in idList
                set pid to contents of pid
                if pid is not "" then
                    try
                        set t to (first track of library playlist 1 whose persistent ID is pid)
                        duplicate t to p
                        set added to added + 1
                    end try
                end if
            end repeat
        end timeout
    end tell
    return added
end run
'''

CLEAN_SCRIPT = r'''
on run argv
    set prefix to item 1 of argv
    tell application "Music"
        set removed to 0
        repeat with p in (get every user playlist whose name starts with prefix)
            delete p
            set removed to removed + 1
        end repeat
    end tell
    return removed
end run
'''


def _osascript(script, *args):
    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False, encoding="utf-8") as f:
        f.write(script)
        path = f.name
    try:
        r = subprocess.run(["osascript", path, *args], capture_output=True, text=True)
    finally:
        Path(path).unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def build_playlists(assignments, dry_run=False, only=None):
    by_playlist = defaultdict(list)
    for song_id, pls in assignments.items():
        for p in pls:
            by_playlist[p].append(song_id)

    targets = [only] if only else list(PLAYLISTS)
    for name in targets:
        if name not in PLAYLISTS:
            raise SystemExit(f"Unknown playlist '{name}'. Options: {', '.join(PLAYLISTS)}")
        ids = by_playlist.get(name, [])
        full_name = PLAYLIST_PREFIX + name
        if dry_run:
            print(f"[dry run] {full_name}: {len(ids)} songs")
            continue
        print(f"Building {full_name} ({len(ids)} songs)...", end=" ", flush=True)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("\n".join(ids))
            id_file = f.name
        try:
            added = _osascript(BUILD_SCRIPT, full_name, id_file)
            print(f"added {added}")
        except RuntimeError as e:
            print(f"FAILED: {e}")
        finally:
            Path(id_file).unlink(missing_ok=True)


def delete_mood_playlists():
    removed = _osascript(CLEAN_SCRIPT, PLAYLIST_PREFIX)
    print(f"Deleted {removed} playlists starting with '{PLAYLIST_PREFIX}'.")

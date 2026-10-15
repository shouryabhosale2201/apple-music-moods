"""Apple Music mood playlists.

  python main.py all --dry-run     # full pipeline, preview only
  python main.py all               # full pipeline, writes playlists
  python main.py export | tags | classify | build | clean
"""
import argparse

import classify
import lastfm
import library
import playlists


def main():
    ap = argparse.ArgumentParser(description="Build mood playlists from your Apple Music library.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("export", help="Step 1: read your library from the Music app")
    t = sub.add_parser("tags", help="Step 2: fetch Last.fm tags (cached)")
    t.add_argument("--refresh", action="store_true", help="ignore cache and refetch everything")
    for name, help_ in (("classify", "Step 3: assign songs to moods"), ("all", "run every step")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--no-llm", action="store_true", help="rules only, never call the LLM")
        p.add_argument("--llm-all", action="store_true",
                       help="let the LLM decide every song (default when LLM_DECIDES_ALL=True)")
        if name == "all":
            p.add_argument("--dry-run", action="store_true", help="don't touch the Music app")
    b = sub.add_parser("build", help="Step 4: create/refresh playlists in Music")
    b.add_argument("--dry-run", action="store_true")
    b.add_argument("--only", help="build just one playlist, e.g. --only Chill")
    sub.add_parser("clean", help="delete every playlist this tool created")

    args = ap.parse_args()
    use_llm = False if getattr(args, "no_llm", False) else None

    if args.cmd == "export":
        library.export_library()
    elif args.cmd == "tags":
        lastfm.fetch_all(library.load_library(), refresh=args.refresh)
    elif args.cmd == "classify":
        classify.classify_all(library.load_library(), lastfm.load_tags(), use_llm, args.llm_all)
    elif args.cmd == "build":
        playlists.build_playlists(classify.load_classified(), dry_run=args.dry_run, only=args.only)
    elif args.cmd == "clean":
        playlists.delete_mood_playlists()
    elif args.cmd == "all":
        songs = library.export_library()
        tags = lastfm.fetch_all(songs)
        assignments = classify.classify_all(songs, tags, use_llm, args.llm_all)
        playlists.build_playlists(assignments, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

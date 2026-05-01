"""
Smoke-test Instaloader against one profile.

Instagram frequently returns 403/401 on graphql/query without a logged-in session.
Add to .env:
  INSTAGRAM_USERNAME=your_ig_login
  INSTAGRAM_PASSWORD=your_password
Optional (persist session between runs):
  INSTAGRAM_SESSION_FILE=.instagram-session

If you see "Please wait a few minutes" (401 rate limit):
  - Stop; wait 15–60 minutes; don't run Instaloader while scrolling IG in the app.
  - Try: INSTAGRAM_EXTRA_QUERY_SLEEP=12 in .env (extra seconds between GraphQL calls).
  - Or bypass API: save timeline JSON from DevTools → python test_instaloader.py --from-json file.json

Checkpoint login: see scrapers/instagram_scraper.py doc / earlier instructions.
"""

from __future__ import annotations

import argparse
import json
import sys

import instaloader
from instaloader.exceptions import ConnectionException

from scrapers.instagram_scraper import build_instaloader
from scrapers.instagram_timeline_graphql import raw_content_list_from_timeline_graphql


def _print_rate_limit_help() -> None:
    print(
        "\nInstagram returned a short-term rate limit (often 401 + 'wait a few minutes').\n"
        "What usually works:\n"
        "  • Wait at least 15–60 minutes before trying again.\n"
        "  • Avoid using the Instagram app on the same account while scraping.\n"
        "  • Add to .env: INSTAGRAM_EXTRA_QUERY_SLEEP=12  (or 15–20)\n"
        "  • Use a fresh session: complete login in browser, re-save INSTAGRAM_SESSION_FILE.\n"
        "  • Dev fallback: copy GraphQL timeline JSON from DevTools →\n"
        "      python test_instaloader.py --from-json timeline.json --organizer 'ESN Nijmegen'\n",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a few posts from an Instagram profile.")
    parser.add_argument(
        "username",
        nargs="?",
        default="esnnijmegen",
        help="Profile username (no @); ignored with --from-json",
    )
    parser.add_argument("--limit", type=int, default=3, help="Max posts to print")
    parser.add_argument(
        "--from-json",
        metavar="FILE",
        help="Print posts from saved user-timeline GraphQL JSON (no Instaloader fetch)",
    )
    parser.add_argument(
        "--organizer",
        default="Timeline import",
        help="Organizer label when using --from-json",
    )
    args = parser.parse_args()

    if args.from_json:
        try:
            with open(args.from_json, encoding="utf-8") as f:
                payload = json.load(f)
        except OSError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        rows = raw_content_list_from_timeline_graphql(payload, organizer=args.organizer)
        if not rows:
            print("No posts parsed (wrong JSON shape?).", file=sys.stderr)
            sys.exit(1)
        for i, raw in enumerate(rows[: args.limit]):
            cap = (raw.text or "")[:200]
            print(f"--- Post {i + 1} ---")
            print(f"Caption: {cap}{'...' if raw.text and len(raw.text) > 200 else ''}")
            print(f"Image URL: {raw.image_url}")
            print(f"Permalink: {raw.source_url}")
            print()
        return

    L = build_instaloader()
    if not L.context.is_logged_in:
        print(
            "Not logged in. Anonymous access often fails with 403/401.\n"
            "Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD (and optionally INSTAGRAM_SESSION_FILE) in .env.",
            file=sys.stderr,
        )

    profile = instaloader.Profile.from_username(L.context, args.username.lstrip("@"))
    try:
        count = 0
        for post in profile.get_posts():
            if count >= args.limit:
                break
            caption = (post.caption or "")[:200]
            print(f"--- Post {count + 1} ---")
            print(f"Date: {post.date_utc}")
            print(f"Caption: {caption}{'...' if len(post.caption or '') > 200 else ''}")
            print(f"Image URL: {post.url}")
            print()
            count += 1
    except ConnectionException as e:
        err = str(e).lower()
        if "wait a few minutes" in err or "401 unauthorized" in err:
            print(e, file=sys.stderr)
            _print_rate_limit_help()
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()

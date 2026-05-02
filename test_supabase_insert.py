"""Insert one Event via SupabaseClient, then delete it (unless --keep)."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta, time

import httpx

from config.settings import settings as cfg
from db import SupabaseClient
from extraction.schemas import Event


def _print_connect_hints(url: str) -> None:
    from urllib.parse import urlparse

    host = urlparse(url).hostname or "(unparsable URL)"
    print(
        "\nCould not open a TCP connection to Supabase (DNS or network).\n"
        f"  Resolved hostname from SUPABASE_URL: {host!r}\n\n"
        "Fix checklist:\n"
        "  • Copy Project URL from Supabase Dashboard → Settings → API "
        "(format https://<ref>.supabase.co).\n"
        "  • .env must not wrap the URL in quotes incorrectly; spaces stripped automatically.\n"
        "  • If hostname looks wrong, fix SUPABASE_URL and rerun.\n"
        "  • Confirm browser can reach the dashboard and you are online "
        "(VPN/firewall sometimes breaks DNS).\n",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Do not delete the row after insert",
    )
    args = parser.parse_args()

    sample_date = date.today() + timedelta(days=21)
    event = Event(
        title="Pipeline test — Pub Quiz",
        description="Smoke test row from test_supabase_insert.py",
        organizer="Tierney's Irish Pub",
        date=sample_date,
        start_time=time(20, 0),
        category="pub_quiz",
        language="english",
        source_platform="test_supabase_insert",
    )

    try:
        db = SupabaseClient()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    try:
        row = db.insert_event(event)
    except httpx.ConnectError as e:
        _print_connect_hints(cfg.SUPABASE_URL)
        print(f"Detail: {e}", file=sys.stderr)
        sys.exit(2)

    print("Inserted:", row)

    if not args.keep:
        eid = row.get("id")
        if eid:
            db.delete_event_by_id(str(eid))
            print("Deleted test row:", eid)


if __name__ == "__main__":
    main()

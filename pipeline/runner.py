"""Orchestrate: load orgs → scrape → LLM extract → dedupe → Supabase."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

from config.settings import settings
from db import SupabaseClient
from extraction import get_event_extractor
from scrapers import InstagramScraper, JsWebsiteScraper, StaticWebsiteScraper
from scrapers.org_utils import organizer_name

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ORGS_CSV = ROOT / "config" / "Nijmegen Student Organizations Database.csv"


def _orgs_csv_path() -> Path:
    raw = (os.getenv("ORGS_CSV_PATH") or "").strip()
    return Path(raw) if raw else DEFAULT_ORGS_CSV


def load_orgs(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Organizations CSV not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def _website_scraper():
    mode = (os.getenv("WEB_SCRAPER_MODE") or "static").strip().lower()
    if mode == "js":
        return JsWebsiteScraper()
    return StaticWebsiteScraper()


def run_pipeline(*, max_orgs: int | None = None, dry_run: bool = False) -> int:
    csv_path = _orgs_csv_path()
    orgs = load_orgs(csv_path)
    if max_orgs is not None:
        orgs = orgs[: max(0, max_orgs)]

    web = _website_scraper()
    extractor = get_event_extractor()
    db: SupabaseClient | None = None if dry_run else SupabaseClient()

    inserted = 0
    skipped_dup = 0
    errors = 0

    for org in orgs:
        label = organizer_name(org)
        print(f"[org] {label}")

        chunks: list = []

        if not settings.SKIP_INSTAGRAM:
            try:
                chunks.extend(InstagramScraper().scrape(org))
            except Exception as e:
                print(f"  instagram skip: {e}", file=sys.stderr)

        try:
            chunks.extend(web.scrape(org))
        except Exception as e:
            print(f"  web scrape error: {e}", file=sys.stderr)

        if not chunks:
            print("  (no raw pages)")
            continue

        for raw in chunks:
            try:
                events = extractor.extract_events(raw)
            except Exception as e:
                print(f"  llm error ({raw.source_url}): {e}", file=sys.stderr)
                errors += 1
                continue

            if not events:
                print(f"  no events from {raw.source_url}")
                continue

            for ev in events:
                if dry_run:
                    print(f"  [dry-run] {ev.date} | {ev.title!r}")
                    continue
                assert db is not None
                if db.event_exists(
                    title=ev.title,
                    organizer=ev.organizer,
                    event_date=ev.date,
                ):
                    skipped_dup += 1
                    continue
                try:
                    db.insert_event(ev)
                except Exception as e:
                    print(f"  insert error: {e}", file=sys.stderr)
                    errors += 1
                    continue
                inserted += 1
                print(f"  + {ev.date} | {ev.title}")

    print(
        f"Done. inserted={inserted} skipped_duplicates={skipped_dup} errors={errors} dry_run={dry_run}"
    )
    return 0 if errors == 0 else 1


__all__ = ["run_pipeline", "load_orgs", "DEFAULT_ORGS_CSV"]

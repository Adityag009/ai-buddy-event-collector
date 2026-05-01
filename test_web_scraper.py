"""
Quick check: scrape event-focused pages from the first CSV row.

Usage:
  python test_web_scraper.py           # static (fast)
  python test_web_scraper.py --js      # Crawl4AI + Playwright
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from scrapers import JsWebsiteScraper, StaticWebsiteScraper


def load_first_org(csv_path: Path) -> dict[str, str]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader)
    return {k.strip(): (v or "").strip() for k, v in row.items() if k}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).resolve().parent
        / "config"
        / "Nijmegen Student Organizations Database.csv",
    )
    parser.add_argument("--js", action="store_true", help="Use Crawl4AI instead of httpx+BS4")
    args = parser.parse_args()

    org = load_first_org(args.csv)
    scraper = JsWebsiteScraper() if args.js else StaticWebsiteScraper()
    rows = scraper.scrape(org)

    print(f"Org: {org.get('Name')!r}")
    print(f"Website cell: {org.get('Website', '')[:120]!r}...")
    print(f"RawContent chunks: {len(rows)}")
    if not rows:
        print("(empty — bad URLs, blocked, or JS-only if using static mode)")
        return
    for i, r in enumerate(rows, 1):
        text = r.text or ""
        print(f"\n--- chunk {i} [{r.source_platform}] ---")
        print(r.source_url)
        print(text[:1800])
        if len(text) > 1800:
            print(f"... [{len(text)} chars]")


if __name__ == "__main__":
    main()

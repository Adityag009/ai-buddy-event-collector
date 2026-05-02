"""Run scrape → LLM → Supabase pipeline."""

from __future__ import annotations

import argparse
import sys

from pipeline.runner import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect events into Supabase.")
    parser.add_argument(
        "--max-orgs",
        type=int,
        default=None,
        help="Process only the first N organizations from the CSV",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run scraper + LLM but do not write to Supabase",
    )
    args = parser.parse_args()
    code = run_pipeline(max_orgs=args.max_orgs, dry_run=args.dry_run)
    sys.exit(code)


if __name__ == "__main__":
    main()

"""JS-rendered sites: Crawl4AI with the same event-focused URL strategy as static scraper."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.cache_context import CacheMode

from extraction.schemas import RawContent
from scrapers.base import BaseScraper
from scrapers.event_urls import normalize_page_url, ordered_page_candidates
from scrapers.org_utils import organizer_name
from scrapers.url_utils import parse_primary_http_url

MAX_TEXT_CHARS = 48_000
MIN_MEANINGFUL_CHARS = 280
DEFAULT_MAX_PAGES = 6


def _text_from_result(result: Any) -> str:
    md = result.markdown
    text = str(md).strip() if md else ""
    if text:
        return text
    return (
        (result.extracted_content or "")
        or (result.cleaned_html or "")
        or (result.html or "")
    ).strip()


async def _scrape_org_async(
    *,
    seed: str,
    organizer: str,
    scraped_at: str,
    max_chars: int,
    max_pages: int,
) -> list[RawContent]:
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        home_res = await crawler.arun(url=seed, config=run_config)
        if not home_res.success:
            return []

        home_final = home_res.redirected_url or home_res.url or seed
        home_norm = normalize_page_url(home_final)
        home_html = home_res.html or ""
        home_text = _text_from_result(home_res)
        if len(home_text) > max_chars:
            home_text = home_text[:max_chars] + "\n\n[truncated]"

        candidates = ordered_page_candidates(
            seed,
            homepage_html=home_html,
            homepage_final_url=home_final,
        )

        event_rows: list[RawContent] = []
        home_row: RawContent | None = None
        seen_final: set[str] = set()

        for cand in candidates:
            if len(event_rows) >= max_pages:
                break

            cand_norm = normalize_page_url(cand.split("#")[0])
            if cand_norm == home_norm:
                final_u = home_final
                text = home_text
            else:
                res = await crawler.arun(url=cand, config=run_config)
                if not res.success:
                    continue
                final_u = res.redirected_url or res.url or cand
                text = _text_from_result(res)
                if len(text) > max_chars:
                    text = text[:max_chars] + "\n\n[truncated]"

            page_norm = normalize_page_url(final_u)
            if page_norm in seen_final:
                continue
            seen_final.add(page_norm)

            if len(text.strip()) < MIN_MEANINGFUL_CHARS:
                continue

            is_home = page_norm == home_norm
            if is_home and event_rows:
                continue

            plat = "website_js_home" if is_home else "website_js_event"
            raw = RawContent(
                organizer=organizer,
                text=text,
                image_url=None,
                source_url=final_u,
                source_platform=plat,
                scraped_at=scraped_at,
            )
            if is_home:
                home_row = raw
            else:
                event_rows.append(raw)

        if event_rows:
            return event_rows
        if home_row:
            return [home_row]
        return []


class JsWebsiteScraper(BaseScraper):
    """Playwright-backed crawl; prefers /events and similar URLs."""

    def __init__(self, *, max_chars: int = MAX_TEXT_CHARS, max_pages: int = DEFAULT_MAX_PAGES):
        self._max_chars = max_chars
        self._max_pages = max_pages

    def scrape(self, org: dict[str, Any]) -> list[RawContent]:
        seed = parse_primary_http_url(
            org.get("Website") or org.get("website") or org.get("url")
        )
        if not seed:
            return []

        organizer = organizer_name(org)
        now = datetime.now(timezone.utc).isoformat()

        try:
            return asyncio.run(
                _scrape_org_async(
                    seed=seed,
                    organizer=organizer,
                    scraped_at=now,
                    max_chars=self._max_chars,
                    max_pages=self._max_pages,
                )
            )
        except Exception:
            return []

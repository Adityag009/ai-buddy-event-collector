"""Fetch event-focused pages (agenda /events links) with httpx + BeautifulSoup."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from extraction.schemas import RawContent
from scrapers.base import BaseScraper
from scrapers.event_urls import normalize_page_url, ordered_page_candidates
from scrapers.html_extract import html_to_plain_text
from scrapers.org_utils import organizer_name
from scrapers.url_utils import parse_primary_http_url

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; AIBuddyEventCollector/1.0; +student research project)"
)
MAX_TEXT_CHARS = 48_000
MIN_MEANINGFUL_CHARS = 280
DEFAULT_MAX_PAGES = 8


class StaticWebsiteScraper(BaseScraper):
    """
    Prefer URLs that usually carry calendars: /events, /agenda, etc., plus homepage links
    whose href/label mentions events. Falls back to homepage content only if nothing else works.
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        max_chars: int = MAX_TEXT_CHARS,
        max_pages: int = DEFAULT_MAX_PAGES,
        user_agent: str = DEFAULT_UA,
    ):
        self._timeout = timeout
        self._max_chars = max_chars
        self._max_pages = max_pages
        self._user_agent = user_agent

    def scrape(self, org: dict[str, Any]) -> list[RawContent]:
        seed = parse_primary_http_url(
            org.get("Website") or org.get("website") or org.get("url")
        )
        if not seed:
            return []

        organizer = organizer_name(org)
        now = datetime.now(timezone.utc).isoformat()

        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": self._user_agent},
            ) as client:
                home_resp = client.get(seed)
                home_resp.raise_for_status()
                home_html = home_resp.text
                home_final = str(home_resp.url)

                home_norm = normalize_page_url(home_final)
                cache: dict[str, tuple[str, str]] = {home_norm: (home_final, home_html)}
                candidates = ordered_page_candidates(
                    seed,
                    homepage_html=home_html,
                    homepage_final_url=home_final,
                )

                event_rows: list[RawContent] = []
                home_row: RawContent | None = None
                seen_final: set[str] = set()

                for cand in candidates:
                    if len(event_rows) >= self._max_pages:
                        break

                    key = normalize_page_url(cand.split("#")[0])
                    if key in cache:
                        final_u, html = cache[key]
                    else:
                        try:
                            resp = client.get(cand)
                            resp.raise_for_status()
                            final_u = str(resp.url)
                            html = resp.text
                            cache[normalize_page_url(final_u)] = (final_u, html)
                        except (httpx.HTTPError, OSError):
                            continue

                    page_norm = normalize_page_url(final_u)
                    if page_norm in seen_final:
                        continue
                    seen_final.add(page_norm)

                    is_home = page_norm == home_norm
                    if is_home and event_rows:
                        continue

                    text = html_to_plain_text(html, max_chars=self._max_chars)
                    if len(text.strip()) < MIN_MEANINGFUL_CHARS:
                        continue

                    plat = "website_static_home" if is_home else "website_static_event"
                    raw = RawContent(
                        organizer=organizer,
                        text=text,
                        image_url=None,
                        source_url=final_u,
                        source_platform=plat,
                        scraped_at=now,
                    )
                    if is_home:
                        home_row = raw
                    else:
                        event_rows.append(raw)

        except (httpx.HTTPError, OSError):
            return []

        if event_rows:
            return event_rows
        if home_row:
            return [home_row]
        return []

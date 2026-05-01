"""Discover URLs likely to contain calendars / event listings."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Common paths for Dutch / EN student / venue sites
EVENT_PATH_SUFFIXES: tuple[str, ...] = (
    "/events",
    "/events/",
    "/event",
    "/event/",
    "/agenda",
    "/agenda/",
    "/calendar",
    "/kalender",
    "/activiteiten",
    "/activities",
    "/programma",
    "/programme",
    "/program",
    "/whats-on",
    "/news/events",
    "/nieuws/events",
    "/evenementen",
)

LINK_HINT = re.compile(
    r"event|agenda|calendar|kalender|activit|programma|evenement|what.?on|"
    r"excursion|trip|borrel|signup|inschrijven",
    re.IGNORECASE,
)


def normalize_page_url(url: str) -> str:
    p = urlparse(url)
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return f"{p.scheme.lower()}://{p.netloc.lower()}{path}"


def site_origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def suffix_url_candidates(origin: str) -> list[str]:
    root = origin.rstrip("/")
    out: list[str] = []
    for suf in EVENT_PATH_SUFFIXES:
        s = suf if suf.startswith("/") else f"/{suf}"
        out.append(urljoin(root + "/", s.lstrip("/")))
    return out


def link_event_candidates(
    homepage_html: str,
    page_final_url: str,
    *,
    max_links: int = 14,
) -> list[str]:
    soup = BeautifulSoup(homepage_html, "html.parser")
    netloc = urlparse(page_final_url).netloc.lower()
    seen: set[str] = set()
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        label = a.get_text(" ", strip=True)
        if not LINK_HINT.search(href) and not LINK_HINT.search(label):
            continue
        full = urljoin(page_final_url, href)
        pu = urlparse(full)
        if pu.scheme not in ("http", "https"):
            continue
        if pu.netloc.lower() != netloc:
            continue
        path_lower = (pu.path or "").lower()
        # Skip committee/about pages; dated listings usually live under /events, /agenda, etc.
        if "/committees/" in path_lower or "/committee/" in path_lower:
            continue
        key = full.split("#")[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
        if len(out) >= max_links:
            break
    return out


def ordered_page_candidates(
    seed_url: str,
    *,
    homepage_html: str | None,
    homepage_final_url: str | None,
) -> list[str]:
    """
    Fetch order: curated paths → homepage links → homepage root (last fallback).
    Deduped.
    """
    origin = site_origin(seed_url)
    tier_suffix = suffix_url_candidates(origin)
    tier_links: list[str] = []
    home = (homepage_final_url or seed_url).split("#")[0]
    if homepage_html:
        tier_links = link_event_candidates(homepage_html, home)
    tier_home = [home.rstrip("/")]

    ordered: list[str] = []
    seen: set[str] = set()
    for tier in (tier_suffix, tier_links, tier_home):
        for u in tier:
            u = u.split("#")[0]
            nu = normalize_page_url(u)
            if nu in seen:
                continue
            seen.add(nu)
            ordered.append(u)
    return ordered

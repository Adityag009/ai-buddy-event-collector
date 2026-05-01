"""Extract HTTP(S) URLs from messy CSV / markdown cells."""

from __future__ import annotations

import re

_URL_RE = re.compile(r"https?://[^\s\]\)\"'<>]+", re.IGNORECASE)


def parse_http_urls(cell: str | None) -> list[str]:
    if not cell or not str(cell).strip():
        return []
    raw = str(cell).strip()
    found = _URL_RE.findall(raw)
    cleaned: list[str] = []
    for u in found:
        u = u.rstrip(".,);]")
        if u and u not in cleaned:
            cleaned.append(u)
    return cleaned


def parse_primary_http_url(cell: str | None) -> str:
    urls = parse_http_urls(cell)
    return urls[0] if urls else ""

"""
Map Instagram user-timeline GraphQL JSON (e.g. xdt_api__v1__feed__user_timeline_graphql_connection)
to RawContent for the LLM pipeline.

Useful if you capture responses from DevTools / Playwright instead of Instaloader's iterator.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from extraction.schemas import RawContent

_TIMELINE_KEY = "xdt_api__v1__feed__user_timeline_graphql_connection"


def _timeline_connection(payload: dict[str, Any]) -> dict[str, Any] | None:
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    conn = data.get(_TIMELINE_KEY)
    if isinstance(conn, dict) and "edges" in conn:
        return conn
    for _k, v in data.items():
        if isinstance(v, dict) and "edges" in v and "timeline" in _k.lower():
            return v
    return None


def raw_content_list_from_timeline_graphql(
    payload: dict[str, Any],
    *,
    organizer: str,
    scraped_at: str | None = None,
) -> list[RawContent]:
    """Parse a full GraphQL response dict into RawContent posts (newest-first as in edges order)."""
    when = scraped_at or datetime.now(timezone.utc).isoformat()
    conn = _timeline_connection(payload)
    if not conn:
        return []

    edges = conn.get("edges")
    if not isinstance(edges, list):
        return []

    out: list[RawContent] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        node = edge.get("node")
        if not isinstance(node, dict):
            continue
        raw = _node_to_raw_content(node, organizer=organizer, scraped_at=when)
        if raw is not None:
            out.append(raw)
    return out


def _node_to_raw_content(
    node: dict[str, Any],
    *,
    organizer: str,
    scraped_at: str,
) -> RawContent | None:
    code = node.get("code")
    if not isinstance(code, str) or not code:
        return None

    text: str | None = None
    cap = node.get("caption")
    if isinstance(cap, dict):
        t = cap.get("text")
        text = t if isinstance(t, str) else None

    image_url: str | None = None
    iv2 = node.get("image_versions2")
    if isinstance(iv2, dict):
        cands = iv2.get("candidates")
        if isinstance(cands, list) and cands:
            first = cands[0]
            if isinstance(first, dict):
                u = first.get("url")
                image_url = u if isinstance(u, str) else None

    return RawContent(
        organizer=organizer,
        text=text,
        image_url=image_url,
        source_url=f"https://www.instagram.com/p/{code}/",
        source_platform="instagram",
        scraped_at=scraped_at,
    )

"""Shared parsing and prompts for event extraction LLMs."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from extraction.schemas import Event, RawContent

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)```\s*$", re.DOTALL)

EVENT_CATEGORIES = (
    "social, pub_quiz, board_games, sports, cultural, food, music, workshop, "
    "party, language_exchange, networking, religious, other"
)

SYSTEM_PROMPT = (
    "You extract structured event listings for a student app in Nijmegen, Netherlands. "
    "Output strict JSON only. Each event must reflect real gatherings with a concrete date."
)


def strip_json_fence(text: str) -> str:
    text = text.strip()
    m = _FENCE_RE.match(text)
    if m:
        return m.group(1).strip()
    return text


def extraction_user_prompt(raw: RawContent) -> str:
    return (
        f"Organizer (trusted): {raw.organizer}\n"
        f"Source URL: {raw.source_url or ''}\n"
        f"Platform: {raw.source_platform}\n\n"
        f"Post text / caption:\n{raw.text or '(empty)'}\n\n"
        "Extract zero or more real-world events advertised here. "
        'Respond with a JSON object: {"events": [ ... ]}. '
        "Each event: title, description (optional), organizer, date (YYYY-MM-DD), "
        "start_time (HH:MM or null), end_time (optional), location_name, address, category, "
        "cost, language, source_url, source_platform, image_url. "
        f"category must be one of: {EVENT_CATEGORIES}. "
        "Use null for unknown optional fields. "
        "Skip items that are not actual dated gatherings."
    )


def parse_events_json(text: str, fallback_organizer: str) -> list[Event]:
    raw = strip_json_fence(text)
    data = json.loads(raw)
    if isinstance(data, dict) and "events" in data:
        items = data["events"]
    elif isinstance(data, list):
        items = data
    else:
        return []

    events: list[Event] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        merged = dict(item)
        if not merged.get("organizer"):
            merged["organizer"] = fallback_organizer
        try:
            events.append(Event.model_validate(merged))
        except ValidationError:
            continue
    return events

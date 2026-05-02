from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urlparse

from supabase import Client, create_client

from config.settings import Settings, settings as default_settings
from extraction.schemas import Event


def _assert_usable_supabase_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme not in ("https", "http"):
        raise ValueError(
            "SUPABASE_URL must start with https:// "
            "(e.g. https://YOUR_PROJECT_REF.supabase.co)."
        )
    if not (p.hostname or "").strip():
        raise ValueError(
            "SUPABASE_URL has no hostname. Use Dashboard → Settings → API → Project URL."
        )


class SupabaseClient:
    """Thin wrapper around Supabase `events` table (schema matches extraction.Event)."""

    def __init__(self, s: Settings | None = None):
        self._settings = s or default_settings
        url = (self._settings.SUPABASE_URL or "").strip()
        key = (self._settings.SUPABASE_KEY or "").strip()
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in the environment or .env"
            )
        _assert_usable_supabase_url(url)
        self._client: Client = create_client(url, key)

    @property
    def client(self) -> Client:
        return self._client

    def insert_event(self, event: Event) -> dict[str, Any]:
        row = _event_to_row(event)
        res = self._client.table("events").insert(row).execute()
        if not res.data:
            raise RuntimeError("Supabase insert returned no rows")
        return res.data[0]

    def insert_events(self, events: list[Event]) -> list[dict[str, Any]]:
        if not events:
            return []
        rows = [_event_to_row(e) for e in events]
        res = self._client.table("events").insert(rows).execute()
        return list(res.data or [])

    def event_exists(self, *, title: str, organizer: str, event_date: date) -> bool:
        res = (
            self._client.table("events")
            .select("id")
            .eq("title", title)
            .eq("organizer", organizer)
            .eq("date", event_date.isoformat())
            .limit(1)
            .execute()
        )
        return bool(res.data)

    def get_events_by_organizer(self, organizer: str) -> list[dict[str, Any]]:
        res = (
            self._client.table("events")
            .select("*")
            .eq("organizer", organizer)
            .execute()
        )
        return list(res.data or [])

    def delete_event_by_id(self, event_id: str) -> None:
        self._client.table("events").delete().eq("id", event_id).execute()


def _event_to_row(event: Event) -> dict[str, Any]:
    """Serialize Event for PostgREST (ISO dates/times, omit nulls)."""
    return event.model_dump(mode="json", exclude_none=True)

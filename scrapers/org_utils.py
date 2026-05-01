"""Helpers for organization rows (CSV dicts)."""

from __future__ import annotations

from typing import Any


def organizer_name(org: dict[str, Any]) -> str:
    return str(
        org.get("Name")
        or org.get("name")
        or org.get("Organization")
        or org.get("organization")
        or "Unknown"
    ).strip()

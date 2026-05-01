"""Smoke-test LLM event extraction (Ollama: LLM_PROVIDER=ollama, Ollama running)."""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timedelta, timezone

from config.settings import settings
from extraction import get_event_extractor
from extraction.schemas import RawContent


def main() -> None:
    # Needs a concrete calendar date — prompts ask the model to skip undated / recurring-only blurbs.
    sample_day = (datetime.now(timezone.utc) + timedelta(days=14)).date().isoformat()
    raw = RawContent(
        organizer="Tierney's Irish Pub",
        text=(
            f"Pub quiz on {sample_day} at 20:00. Nijmegen city centre. "
            "Teams of max 4, free entry."
        ),
        source_url="https://example.com/post",
        source_platform="manual_test",
        scraped_at=datetime.now(timezone.utc).isoformat(),
    )

    prov = settings.LLM_PROVIDER.strip().lower()
    model = (
        settings.OLLAMA_MODEL
        if prov == "ollama"
        else settings.GEMINI_MODEL
        if prov == "gemini"
        else settings.OPENAI_MODEL
    )
    print(f"LLM_PROVIDER={settings.LLM_PROVIDER!r} model={model!r}", flush=True)

    try:
        extractor = get_event_extractor()
        events = extractor.extract_events(raw)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        sys.exit(1)

    if not events:
        print(
            "No events parsed (empty list).\n"
            "Common causes: model returned [] because text had no concrete date; "
            "invalid JSON; or fields failed Pydantic validation (check raw model output with --verbose).",
            flush=True,
        )
        sys.exit(1)

    for e in events:
        print(e.model_dump_json(indent=2), flush=True)


if __name__ == "__main__":
    main()

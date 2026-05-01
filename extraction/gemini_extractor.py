from __future__ import annotations

from typing import Optional

import httpx
from google import genai
from google.genai import types

from extraction.base_llm import BaseLLMExtractor
from extraction.llm_utils import SYSTEM_PROMPT, extraction_user_prompt, parse_events_json
from extraction.schemas import Event, RawContent


def _image_part(url: str | None) -> Optional[types.Part]:
    if not url:
        return None
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
        ctype = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if not ctype.startswith("image/"):
            ctype = "image/jpeg"
        return types.Part.from_bytes(data=r.content, mime_type=ctype)
    except (httpx.HTTPError, OSError, ValueError):
        return None


class GeminiEventExtractor(BaseLLMExtractor):
    def __init__(self, api_key: str, model: str | None = None):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for LLM_PROVIDER=gemini")
        self._client = genai.Client(api_key=api_key)
        self._model = model or "gemini-2.0-flash"

    def extract_events(self, raw_content: RawContent) -> list[Event]:
        parts: list[types.Part] = [
            types.Part.from_text(text=extraction_user_prompt(raw_content)),
        ]
        img = _image_part(raw_content.image_url)
        if img is not None:
            parts.append(img)

        response = self._client.models.generate_content(
            model=self._model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        text = response.text or "{}"
        return parse_events_json(text, raw_content.organizer)

from __future__ import annotations

from typing import Any

import httpx

from extraction.base_llm import BaseLLMExtractor
from extraction.llm_utils import SYSTEM_PROMPT, extraction_user_prompt, parse_events_json
from extraction.schemas import Event, RawContent


def chat_completions_url_from_base(base: str) -> str:
    """Normalize host or /v1 prefix into .../v1/chat/completions (OpenAI + Ollama compat)."""
    b = base.rstrip("/")
    if b.endswith("/chat/completions"):
        return b
    if b.endswith("/v1"):
        return f"{b}/chat/completions"
    return f"{b}/v1/chat/completions"


class OpenAIChatExtractor(BaseLLMExtractor):
    """
    OpenAI Chat Completions schema — works for api.openai.com and any compatible server
    (Ollama: LLM_PROVIDER=ollama uses .../v1/chat/completions; swap models via env).

    Same idea as LangChain ChatOpenAI(base_url=f'{OLLAMA_URL}/v1', api_key='not-needed', model=...).
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1/chat/completions",
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ):
        self._api_key = api_key or "ollama"
        self._model = model
        self._url = chat_completions_url_from_base(base_url)
        self._temperature = temperature
        self._max_tokens = max_tokens

    def extract_events(self, raw_content: RawContent) -> list[Event]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": extraction_user_prompt(raw_content)},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=180.0) as client:
            r = client.post(self._url, headers=headers, json=payload)
            r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return parse_events_json(text, raw_content.organizer)

from __future__ import annotations

from config.settings import Settings, settings as default_settings
from extraction.base_llm import BaseLLMExtractor
from extraction.gemini_extractor import GeminiEventExtractor
from extraction.openai_extractor import OpenAIChatExtractor, chat_completions_url_from_base


def get_event_extractor(settings: Settings | None = None) -> BaseLLMExtractor:
    s = settings or default_settings
    name = (s.LLM_PROVIDER or "gemini").strip().lower()

    if name == "gemini":
        return GeminiEventExtractor(api_key=s.GEMINI_API_KEY, model=s.GEMINI_MODEL)

    if name == "openai":
        if not (s.OPENAI_API_KEY or "").strip():
            raise ValueError("OPENAI_API_KEY is required for LLM_PROVIDER=openai")
        return OpenAIChatExtractor(
            api_key=s.OPENAI_API_KEY,
            model=s.OPENAI_MODEL,
            base_url=s.OPENAI_BASE_URL,
            temperature=s.LLM_TEMPERATURE,
            max_tokens=s.LLM_MAX_TOKENS,
        )

    if name == "ollama":
        # OpenAI-compatible server bundled with Ollama (POST .../v1/chat/completions)
        url = chat_completions_url_from_base(s.OLLAMA_URL)
        key = (s.OLLAMA_OPENAI_API_KEY or "ollama").strip()
        return OpenAIChatExtractor(
            api_key=key,
            model=s.OLLAMA_MODEL,
            base_url=url,
            temperature=s.LLM_TEMPERATURE,
            max_tokens=s.LLM_MAX_TOKENS,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER={name!r}. Use gemini, openai, or ollama."
    )

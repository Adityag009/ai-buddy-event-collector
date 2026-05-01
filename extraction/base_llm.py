from __future__ import annotations

from abc import ABC, abstractmethod

from extraction.schemas import Event, RawContent


class BaseLLMExtractor(ABC):
    """Swap implementations via LLM_PROVIDER in settings (gemini, openai, ollama)."""

    @abstractmethod
    def extract_events(self, raw_content: RawContent) -> list[Event]:
        raise NotImplementedError

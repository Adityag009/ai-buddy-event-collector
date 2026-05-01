"""LLM event extraction: choose backend via LLM_PROVIDER (gemini | openai | ollama)."""

from extraction.base_llm import BaseLLMExtractor
from extraction.factory import get_event_extractor

__all__ = ["BaseLLMExtractor", "get_event_extractor"]

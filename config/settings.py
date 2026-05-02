import os
from dotenv import load_dotenv

load_dotenv()


def _env_float(key: str, default: float = 0.0) -> float:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_strip(key: str) -> str:
    """Trim whitespace and outer quotes often pasted into .env by mistake."""
    v = (os.getenv(key, "") or "").strip()
    if len(v) >= 2 and v[0] in "\"'" and v[0] == v[-1]:
        v = v[1:-1].strip()
    return v


def _normalize_https_base(url: str) -> str:
    u = url.strip().rstrip("/")
    if not u:
        return u
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


# Ollama / LangChain-style: OLLAMA_URL + /v1 (see extraction.openai_extractor.chat_completions_url_from_base)
_ollama_host = (
    os.getenv("OLLAMA_URL", "").strip()
    or os.getenv("OLLAMA_BASE_URL", "").strip()
    or "http://127.0.0.1:11434"
).rstrip("/")


class Settings:
    SUPABASE_URL: str = _normalize_https_base(_env_strip("SUPABASE_URL"))
    SUPABASE_KEY: str = _env_strip("SUPABASE_KEY")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_TEMPERATURE: float = _env_float("LLM_TEMPERATURE", 0.3)
    LLM_MAX_TOKENS: int = _env_int("LLM_MAX_TOKENS", 1024)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL: str = os.getenv(
        "OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"
    )
    OLLAMA_URL: str = _ollama_host
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    # Bearer token sent to Ollama OpenAI-compat endpoint (value ignored by Ollama)
    OLLAMA_OPENAI_API_KEY: str = os.getenv("OLLAMA_OPENAI_API_KEY", "ollama")
    APP_MODE: str = os.getenv("APP_MODE", "")
    SKIP_INSTAGRAM: bool = os.getenv("SKIP_INSTAGRAM", "").lower() in (
        "1",
        "true",
        "yes",
    )
    INSTAGRAM_USERNAME: str = os.getenv("INSTAGRAM_USERNAME", "")
    INSTAGRAM_PASSWORD: str = os.getenv("INSTAGRAM_PASSWORD", "")
    INSTAGRAM_SESSION_FILE: str = os.getenv("INSTAGRAM_SESSION_FILE", "")
    INSTAGRAM_SESSION_ONLY: bool = os.getenv("INSTAGRAM_SESSION_ONLY", "").lower() in (
        "1",
        "true",
        "yes",
    )
    INSTAGRAM_EXTRA_QUERY_SLEEP: float = _env_float("INSTAGRAM_EXTRA_QUERY_SLEEP", 0.0)
    IS_DEMO: bool = os.getenv("APP_MODE", "").strip().lower() == "demo"


settings = Settings()

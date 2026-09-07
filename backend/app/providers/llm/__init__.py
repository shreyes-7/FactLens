"""
LLM Provider Factory.
Instantiates the configured LLM provider according to settings.
"""

from backend.app.config import Settings, get_settings
from backend.app.providers.llm.base import LLMProvider
from backend.app.providers.llm.groq import GroqProvider
from backend.app.providers.llm.gemini import GeminiProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """
    Factory function returning the configured LLM provider.
    Defaults to Groq as the primary LLM provider.
    """
    cfg = settings or get_settings()

    if cfg.llm_provider == "groq":
        if not cfg.groq_api_key:
            raise ValueError("Cannot initialize GroqProvider: missing GROQ_API_KEY.")
        return GroqProvider(
            api_key=cfg.groq_api_key,
            model=cfg.groq_model,
        )
    elif cfg.llm_provider == "gemini":
        if not cfg.llm_api_key:
            raise ValueError("Cannot initialize GeminiProvider: missing LLM_API_KEY.")
        return GeminiProvider(
            api_key=cfg.llm_api_key,
            model=cfg.llm_model or "gemini-1.5-flash",
        )
    else:
        raise ValueError(f"Unsupported LLM provider: '{cfg.llm_provider}'. Supported: 'groq', 'gemini'.")


__all__ = ["LLMProvider", "GroqProvider", "GeminiProvider", "get_llm_provider"]

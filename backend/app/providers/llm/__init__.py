"""
LLM Provider Factory.
Instantiates the configured LLM provider according to settings,
with optional automatic fallback between Gemini and Groq if fallback is enabled.
"""

from backend.app.config import Settings, get_settings
from backend.app.providers.llm.base import LLMProvider
from backend.app.providers.llm.fallback import FallbackLLMProvider
from backend.app.providers.llm.gemini import GeminiProvider
from backend.app.providers.llm.groq import GroqProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """
    Factory function returning the configured LLM provider.
    If llm_fallback_enabled is True and both keys are available, returns FallbackLLMProvider.
    """
    cfg = settings or get_settings()

    gemini_instance = None
    if cfg.llm_api_key and cfg.llm_api_key.strip():
        gemini_instance = GeminiProvider(
            api_key=cfg.llm_api_key,
            model=cfg.llm_model or "gemini-flash-latest",
        )

    groq_instance = None
    if cfg.groq_api_key and cfg.groq_api_key.strip():
        groq_instance = GroqProvider(
            api_key=cfg.groq_api_key,
            model=cfg.groq_model or "openai/gpt-oss-120b",
        )

    if cfg.llm_provider == "gemini":
        if not gemini_instance:
            raise ValueError("Cannot initialize GeminiProvider: missing LLM_API_KEY.")
        if cfg.llm_fallback_enabled and groq_instance:
            return FallbackLLMProvider(primary=gemini_instance, fallback=groq_instance)
        return gemini_instance

    elif cfg.llm_provider == "groq":
        if not groq_instance:
            raise ValueError("Cannot initialize GroqProvider: missing GROQ_API_KEY.")
        if cfg.llm_fallback_enabled and gemini_instance:
            return FallbackLLMProvider(primary=groq_instance, fallback=gemini_instance)
        return groq_instance

    else:
        raise ValueError(f"Unsupported LLM provider: '{cfg.llm_provider}'. Supported: 'groq', 'gemini'.")


__all__ = [
    "LLMProvider",
    "GroqProvider",
    "GeminiProvider",
    "FallbackLLMProvider",
    "get_llm_provider",
]

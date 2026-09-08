"""
Unit tests for LLM providers and factory.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock
from backend.app.config import Settings
from backend.app.providers.llm import get_llm_provider, GroqProvider, GeminiProvider


def test_factory_returns_groq_by_default():
    """Verify factory returns GroqProvider with configured model when LLM_PROVIDER=groq and fallback is disabled."""
    settings = Settings(
        _env_file=None,
        llm_provider="groq",
        groq_api_key="gsk_test_key",
        groq_model="openai/gpt-oss-120b",
        jina_api_key="jina_key",
        llm_fallback_enabled=False,
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, GroqProvider)
    assert provider.provider_name == "groq"
    assert provider.model_name == "openai/gpt-oss-120b"


def test_factory_returns_gemini_when_configured():
    """Verify factory returns GeminiProvider when LLM_PROVIDER=gemini and fallback is disabled."""
    settings = Settings(
        _env_file=None,
        llm_provider="gemini",
        llm_api_key="gemini_key",
        groq_api_key="gsk_key",
        jina_api_key="jina_key",
        llm_fallback_enabled=False,
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, GeminiProvider)
    assert provider.provider_name == "gemini"


@pytest.mark.asyncio
async def test_groq_generate_mocked():
    """Verify GroqProvider sends correct payload to Groq API."""
    provider = GroqProvider(api_key="gsk_mock_key", model="openai/gpt-oss-120b")

    mock_response = httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"content": "Grounded answer from Groq"}}]},
        request=httpx.Request("POST", provider.BASE_URL),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await provider.generate("Test prompt", system_prompt="Test system")

        assert result == "Grounded answer from Groq"
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "openai/gpt-oss-120b"
        assert call_kwargs["headers"]["Authorization"] == "Bearer gsk_mock_key"


def test_factory_returns_fallback_provider_when_enabled():
    """Verify factory returns FallbackLLMProvider when llm_fallback_enabled is True."""
    from backend.app.providers.llm.fallback import FallbackLLMProvider

    settings = Settings(
        _env_file=None,
        llm_provider="gemini",
        llm_api_key="gemini_key",
        groq_api_key="gsk_key",
        jina_api_key="jina_key",
        llm_fallback_enabled=True,
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, FallbackLLMProvider)
    assert "gemini" in provider.provider_name
    assert "groq" in provider.provider_name


@pytest.mark.asyncio
async def test_fallback_provider_fails_over_to_secondary():
    """Verify FallbackLLMProvider transparently falls back when primary fails."""
    from backend.app.providers.llm.fallback import FallbackLLMProvider

    class FailingPrimary:
        provider_name = "failing_primary"
        model_name = "failing_model"

        async def generate(self, prompt, system_prompt=None):
            raise RuntimeError("Primary 503 Outage")

    class WorkingFallback:
        provider_name = "working_fallback"
        model_name = "working_model"

        async def generate(self, prompt, system_prompt=None):
            return "Fallback answer"

    fb = FallbackLLMProvider(primary=FailingPrimary(), fallback=WorkingFallback())
    result = await fb.generate("Test")
    assert result == "Fallback answer"


@pytest.mark.asyncio
async def test_gemini_timeout_fails_fast_without_retries():
    """Verify GeminiProvider raises RuntimeError immediately on ReadTimeout without looping through 3 retries."""
    provider = GeminiProvider(api_key="mock_key", timeout=15.0, max_retries=3)

    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.ReadTimeout("Read timed out")) as mock_post:
        with pytest.raises(RuntimeError, match="timed out"):
            await provider.generate("Extract facts")

        # Must have attempted only once, failing fast to secondary provider
        assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_gemini_timeout_with_fallback_triggers_groq():
    """Verify FallbackLLMProvider switches to Groq immediately when Gemini encounters ReadTimeout."""
    from backend.app.providers.llm.fallback import FallbackLLMProvider

    gemini = GeminiProvider(api_key="mock_gemini", timeout=15.0)
    groq = GroqProvider(api_key="mock_groq")

    with patch.object(httpx.AsyncClient, "post") as mock_post:
        # First call (Gemini) times out; second call (Groq) succeeds
        mock_post.side_effect = [
            httpx.ReadTimeout("Read timed out"),
            httpx.Response(
                status_code=200,
                json={"choices": [{"message": {"content": "Fast answer from Groq"}}]},
                request=httpx.Request("POST", groq.BASE_URL),
            ),
        ]

        fb = FallbackLLMProvider(primary=gemini, fallback=groq)
        res = await fb.generate("Extract facts")

        assert res == "Fast answer from Groq"
        assert mock_post.call_count == 2


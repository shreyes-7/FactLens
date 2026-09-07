"""
Unit tests for LLM providers and factory.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock
from backend.app.config import Settings
from backend.app.providers.llm import get_llm_provider, GroqProvider, GeminiProvider


def test_factory_returns_groq_by_default():
    """Verify factory returns GroqProvider with configured model when LLM_PROVIDER=groq."""
    settings = Settings(
        llm_provider="groq",
        groq_api_key="gsk_test_key",
        groq_model="openai/gpt-oss-120b",
        jina_api_key="jina_key",
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, GroqProvider)
    assert provider.provider_name == "groq"
    assert provider.model_name == "openai/gpt-oss-120b"


def test_factory_returns_gemini_when_configured():
    """Verify factory returns GeminiProvider when LLM_PROVIDER=gemini."""
    settings = Settings(
        llm_provider="gemini",
        llm_api_key="gemini_key",
        groq_api_key="gsk_key",
        jina_api_key="jina_key",
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

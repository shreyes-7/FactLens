"""
Unit tests for FactLens configuration.
"""

import pytest
from backend.app.config import Settings


def test_config_groq_and_jina_defaults():
    """Verify default provider selections are Groq and Jina with 1024 dimensions."""
    settings = Settings(
        _env_file=None,
        groq_api_key="gsk_test_key",
        jina_api_key="jina_test_key",
    )
    assert settings.llm_provider == "groq"
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert settings.embedding_provider == "jina"
    assert settings.embedding_model == "jina-embeddings-v3"
    assert settings.embedding_dimension == 1024



def test_groq_requires_api_key():
    """Verify Groq raises ValueError if GROQ_API_KEY is missing."""
    with pytest.raises(ValueError, match="GROQ_API_KEY environment variable is required"):
        Settings(
            llm_provider="groq",
            groq_api_key="",
            jina_api_key="jina_test_key",
        )


def test_gemini_not_required_when_groq_selected():
    """Verify Gemini API key is not required when Groq is the selected provider."""
    settings = Settings(
        llm_provider="groq",
        groq_api_key="gsk_valid_key",
        jina_api_key="jina_valid_key",
        llm_api_key=None,
    )
    assert settings.llm_provider == "groq"
    assert settings.llm_api_key is None


def test_gemini_requires_api_key_when_gemini_selected():
    """Verify Gemini raises ValueError only when selected as provider without key."""
    with pytest.raises(ValueError, match="LLM_API_KEY environment variable is required"):
        Settings(
            llm_provider="gemini",
            llm_api_key=None,
            groq_api_key="gsk_key",
            jina_api_key="jina_key",
        )


def test_jina_requires_api_key_and_1024_dimension():
    """Verify Jina raises error when key is missing or dimension is not 1024."""
    with pytest.raises(ValueError, match="JINA_API_KEY environment variable is required"):
        Settings(
            embedding_provider="jina",
            jina_api_key="",
            groq_api_key="gsk_key",
        )

    with pytest.raises(ValueError, match="EMBEDDING_DIMENSION must be 1024 for Jina embeddings"):
        Settings(
            embedding_provider="jina",
            jina_api_key="jina_key",
            groq_api_key="gsk_key",
            embedding_dimension=384,
        )


def test_local_embeddings_do_not_require_jina_key():
    """Verify local embedding provider does not require Jina credentials."""
    settings = Settings(
        embedding_provider="local",
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_dimension=384,
        jina_api_key=None,
        groq_api_key="gsk_key",
    )
    assert settings.embedding_provider == "local"
    assert settings.embedding_dimension == 384


def test_secrets_never_exposed_in_repr():
    """Verify secret keys are masked in string representation."""
    settings = Settings(
        groq_api_key="super_secret_groq_key_12345",
        jina_api_key="super_secret_jina_key_67890",
    )
    rep = repr(settings)
    assert "super_secret_groq_key_12345" not in rep
    assert "super_secret_jina_key_67890" not in rep
    assert "***" in rep

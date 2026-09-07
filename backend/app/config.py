"""
FactLens Configuration Module.
Loads configuration from environment variables with conditional validation
and secret protection.
"""

from functools import lru_cache
from typing import Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "FactLens"
    app_env: str = "development"
    debug: bool = True

    # Database & Storage
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "documents"

    # LLM Settings
    llm_provider: Literal["groq", "gemini", "mock"] = Field(
        default="groq",
        description="Active LLM provider. Groq is the primary default.",
    )
    groq_api_key: str | None = Field(
        default=None,
        description="Groq API key. Required when llm_provider='groq'.",
    )
    groq_model: str = Field(
        default="openai/gpt-oss-120b",
        description="Default Groq model name.",
    )

    # Optional Gemini settings (used only if llm_provider='gemini')
    llm_api_key: str | None = Field(
        default=None,
        description="Gemini API key. Required only when llm_provider='gemini'.",
    )
    llm_model: str | None = Field(
        default=None,
        description="Gemini model name.",
    )
    llm_fallback_enabled: bool = Field(
        default=False,
        description="Enable automatic fallback between Gemini and Groq if both keys are present.",
    )
    fact_extraction_batch_size: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of chunks to batch together in a single LLM fact-extraction request.",
    )

    # Embedding Settings
    embedding_provider: Literal["jina", "local", "mock"] = Field(
        default="jina",
        description="Active embedding provider. Jina AI hosted API is the primary default.",
    )
    embedding_model: str = Field(
        default="jina-embeddings-v3",
        description="Embedding model name.",
    )
    embedding_dimension: int = Field(
        default=1024,
        description="Embedding dimension. 1024 for jina-embeddings-v3, 384 for local BGE.",
    )
    jina_api_key: str | None = Field(
        default=None,
        description="Jina API key. Required when embedding_provider='jina'.",
    )

    # Observability & Logging
    logfire_token: str | None = None
    log_format: Literal["json", "text"] = Field(
        default="text",
        description="Logging format: 'json' for production structured logs, 'text' for development.",
    )

    # Security & Throttling
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable per-IP sliding window rate limiting.",
    )
    rate_limit_per_minute: int = Field(
        default=120,
        description="Maximum allowed requests per minute per IP address.",
    )
    security_headers_enabled: bool = Field(
        default=True,
        description="Inject security response headers (nosniff, DENY, etc.).",
    )
    allowed_cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "*",
        ],
        description="Allowed CORS origin URLs.",
    )

    # Processing Defaults
    max_file_size_mb: int = 50
    chunk_size: int = 1200
    chunk_overlap: int = 150
    top_k_candidates: int = 10

    @model_validator(mode="after")
    def validate_provider_configuration(self) -> "Settings":
        """
        Conditionally validate provider requirements.
        Never require Gemini credentials when Groq is selected.
        Never require local dependencies or local config when Jina is selected.
        """
        # Validate LLM Provider
        if self.llm_provider == "groq":
            if not self.groq_api_key or not self.groq_api_key.strip():
                raise ValueError(
                    "GROQ_API_KEY environment variable is required when LLM_PROVIDER is 'groq'."
                )
        elif self.llm_provider == "gemini":
            if not self.llm_api_key or not self.llm_api_key.strip():
                raise ValueError(
                    "LLM_API_KEY environment variable is required when LLM_PROVIDER is 'gemini'."
                )

        # Validate Embedding Provider
        if self.embedding_provider == "jina":
            if not self.jina_api_key or not self.jina_api_key.strip():
                raise ValueError(
                    "JINA_API_KEY environment variable is required when EMBEDDING_PROVIDER is 'jina'."
                )
            if self.embedding_dimension != 1024:
                raise ValueError(
                    f"EMBEDDING_DIMENSION must be 1024 for Jina embeddings (got {self.embedding_dimension})."
                )
        elif self.embedding_provider == "local":
            if self.embedding_dimension != 384 and "bge-small" in self.embedding_model:
                raise ValueError(
                    f"EMBEDDING_DIMENSION must match model output (expected 384 for {self.embedding_model})."
                )

        return self

    def __repr__(self) -> str:
        """Shield secrets from appearing in logs or error traces."""
        return (
            f"Settings(app_name={self.app_name!r}, "
            f"llm_provider={self.llm_provider!r}, "
            f"groq_model={self.groq_model!r}, "
            f"groq_api_key='***', "
            f"embedding_provider={self.embedding_provider!r}, "
            f"embedding_model={self.embedding_model!r}, "
            f"embedding_dimension={self.embedding_dimension}, "
            f"jina_api_key='***')"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()

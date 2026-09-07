"""
Health check and diagnostics API router.
"""

import logging
from fastapi import APIRouter, Depends
from backend.app.config import Settings, get_settings
from backend.app.database import get_db_connection
from backend.app.providers.embeddings import get_embedding_provider
from backend.app.providers.llm import get_llm_provider
from backend.app.schemas.api import HealthResponse

logger = logging.getLogger("factlens.api.health")

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def get_health_status(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Check database connection and AI provider configuration."""
    db_ok = False
    try:
        conn = get_db_connection(settings)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        conn.close()
        db_ok = True
    except Exception as e:
        logger.error(f"Health check DB probe failed: {e}")

    llm = get_llm_provider(settings)
    emb = get_embedding_provider(settings)

    from backend.app.providers.llm.fallback import FallbackLLMProvider

    primary_provider = getattr(llm, "provider_name", "unknown")
    primary_model = getattr(llm, "model_name", "unknown")
    fallback_provider = None
    fallback_model = None

    if isinstance(llm, FallbackLLMProvider):
        primary_provider = llm.primary.provider_name
        primary_model = llm.primary.model_name
        fallback_provider = llm.fallback.provider_name
        fallback_model = llm.fallback.model_name
    elif settings.llm_fallback_enabled:
        if settings.llm_provider == "gemini" and settings.groq_api_key:
            fallback_provider = "groq"
            fallback_model = settings.groq_model
        elif settings.llm_provider == "groq" and settings.llm_api_key:
            fallback_provider = "gemini"
    overall_status = "ok" if db_ok else "degraded"

    return HealthResponse(
        status=overall_status,
        database_connected=db_ok,
        llm_provider=getattr(llm, "provider_name", "unknown"),
        llm_model=getattr(llm, "model_name", "unknown"),
        fallback_enabled=settings.llm_fallback_enabled,
        primary_provider=primary_provider,
        primary_model=primary_model,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
        embedding_provider=emb.provider_name,
        version="0.1.0",
    )

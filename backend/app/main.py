"""
FactLens FastAPI Core Application.
Evidence-grounded Fact Knowledge Layer API with enterprise-grade observability,
security headers, rate limiting, and structured error handling.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import api_router
from backend.app.config import get_settings
from backend.app.observability.errors import register_error_handlers
from backend.app.observability.logfire_setup import init_logfire
from backend.app.observability.logger import configure_logging, get_logger
from backend.app.observability.middleware import (
    ExecutionTimingMiddleware,
    RequestTracingMiddleware,
)
from backend.app.security.middleware import (
    RateLimitingMiddleware,
    SecurityHeadersMiddleware,
)

logger = get_logger("factlens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan events."""
    settings = get_settings()

    # Configure structured logging with sensitive data redaction
    configure_logging(log_format=settings.log_format)

    logger.info("Starting FactLens Application API...")
    logger.info(f"Environment: {settings.app_env} | Embeddings: {settings.embedding_dimension}-d")
    logger.info(f"LLM Provider: {settings.llm_provider} (Fallback: {settings.llm_fallback_enabled})")
    logger.info(f"Rate Limiting: {'Enabled (' + str(settings.rate_limit_per_minute) + ' req/min)' if settings.rate_limit_enabled else 'Disabled'}")
    logger.info(f"Security Headers: {'Enabled' if settings.security_headers_enabled else 'Disabled'}")

    # Optional Logfire instrumentation
    init_logfire(app, settings)

    yield
    logger.info("Shutting down FactLens Application API...")


settings = get_settings()

app = FastAPI(
    title="FactLens API",
    description=(
        "Evidence-grounded Fact Knowledge Layer for discovering, normalizing, "
        "comparing, and explaining cross-document facts with exact source quotes."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# 1. Register global structured error handlers (RFC-compatible problem details)
register_error_handlers(app)

# 2. Register observability and security middlewares
# Note: Middleware runs in reverse order of addition for requests (LIFO)
app.add_middleware(SecurityHeadersMiddleware, settings=settings)
app.add_middleware(RateLimitingMiddleware, settings=settings)
app.add_middleware(ExecutionTimingMiddleware)
app.add_middleware(RequestTracingMiddleware)

# 3. Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Include master API router under /api
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    """Welcome endpoint pointing to API documentation and system status."""
    return JSONResponse(
        content={
            "app": "FactLens API",
            "version": "0.1.0",
            "description": "Evidence-grounded Fact Knowledge Layer",
            "documentation": "/docs",
            "openapi": "/openapi.json",
            "health": "/api/health",
            "endpoints": {
                "health": "/api/health",
                "datasets": "/api/datasets",
                "documents": "/api/documents",
                "facts": "/api/facts",
                "relationships": "/api/relationships",
                "four_cases": "/api/cases/four-cases",
            },
        }
    )

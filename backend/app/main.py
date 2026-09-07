"""
FactLens FastAPI Core Application.
Evidence-grounded Fact Knowledge Layer API.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import api_router
from backend.app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("factlens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan events."""
    settings = get_settings()
    logger.info("Starting FactLens Application API...")
    logger.info(f"Environment: {settings.environment} | Embeddings: {settings.embedding_dimension}-d")
    logger.info(f"LLM Provider: {settings.llm_provider} (Fallback: {settings.llm_fallback_enabled})")
    yield
    logger.info("Shutting down FactLens Application API...")


app = FastAPI(
    title="FactLens API",
    description=(
        "Evidence-grounded Fact Knowledge Layer for discovering, normalizing, "
        "comparing, and explaining cross-document facts with exact source quotes."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for local development and Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include master API router under /api
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

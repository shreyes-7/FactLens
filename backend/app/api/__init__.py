"""
Master API router bundling all endpoint sub-routers under /api.
"""

from fastapi import APIRouter
from backend.app.api.cases import router as cases_router
from backend.app.api.datasets import router as datasets_router
from backend.app.api.documents import router as documents_router
from backend.app.api.facts import router as facts_router
from backend.app.api.health import router as health_router
from backend.app.api.relationships import router as relationships_router
from backend.app.api.comparisons import router as comparisons_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(datasets_router)
api_router.include_router(documents_router)
api_router.include_router(facts_router)
api_router.include_router(relationships_router)
api_router.include_router(comparisons_router)
api_router.include_router(cases_router)

__all__ = ["api_router"]

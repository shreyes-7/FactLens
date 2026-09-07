"""
Pydantic Logfire integration setup for FactLens.
Adheres to Architecture Rules Section 41: Observability.
"""

from fastapi import FastAPI
from backend.app.config import Settings
from backend.app.observability.logger import get_logger

logger = get_logger("factlens.observability")


def init_logfire(app: FastAPI, settings: Settings) -> bool:
    """
    Conditionally initialize Pydantic Logfire if a token is configured.
    Falls back gracefully to native structured logging when absent.
    """
    token = settings.logfire_token
    if not token or not token.strip():
        logger.info("Logfire token not provided; operating with native structured logging.")
        return False

    try:
        import logfire
        logfire.configure(token=token, service_name=settings.app_name)
        logfire.instrument_fastapi(app)
        logfire.instrument_pydantic()
        logfire.instrument_httpx()
        logger.info("Pydantic Logfire instrumentation successfully active (FastAPI, Pydantic, HTTPX).")
        return True
    except Exception as exc:
        logger.warning(f"Failed to initialize Pydantic Logfire: {exc}. Falling back to structured logging.")
        return False

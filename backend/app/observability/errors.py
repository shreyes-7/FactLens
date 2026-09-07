"""
Error classification taxonomy and standardized exception handling for FactLens.
Adheres to Architecture Rules Section 43: Error Handling.
"""

from enum import Enum
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.app.observability.logger import get_logger, mask_sensitive_data, request_id_ctx

logger = get_logger("factlens.errors")


class ErrorCategory(str, Enum):
    """
    Standard error categories for classified failure reporting.
    """
    INVALID_FILE = "INVALID_FILE"
    PDF_PARSE_ERROR = "PDF_PARSE_ERROR"
    EMPTY_DOCUMENT = "EMPTY_DOCUMENT"
    LLM_ERROR = "LLM_ERROR"
    LLM_INVALID_OUTPUT = "LLM_INVALID_OUTPUT"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    REASONING_ERROR = "REASONING_ERROR"


# Default HTTP status code mapping per error category
CATEGORY_HTTP_STATUS = {
    ErrorCategory.INVALID_FILE: status.HTTP_400_BAD_REQUEST,
    ErrorCategory.PDF_PARSE_ERROR: 422,
    ErrorCategory.EMPTY_DOCUMENT: 422,
    ErrorCategory.LLM_ERROR: status.HTTP_502_BAD_GATEWAY,
    ErrorCategory.LLM_INVALID_OUTPUT: status.HTTP_502_BAD_GATEWAY,
    ErrorCategory.EMBEDDING_ERROR: status.HTTP_502_BAD_GATEWAY,
    ErrorCategory.STORAGE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCategory.DATABASE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCategory.REASONING_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


class FactLensAPIException(Exception):
    """Base application exception with structured error categorization."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.status_code = status_code or CATEGORY_HTTP_STATUS.get(category, 500)
        self.context = context or {}


def register_error_handlers(app: FastAPI) -> None:
    """Register structured exception handlers on the FastAPI application."""

    @app.exception_handler(FactLensAPIException)
    async def factlens_exception_handler(request: Request, exc: FactLensAPIException):
        req_id = request_id_ctx.get()
        logger.warning(
            f"[{exc.category.value}] {exc.message} (status={exc.status_code}, path={request.url.path})"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": mask_sensitive_data(exc.message),
                "error": {
                    "category": exc.category.value,
                    "message": mask_sensitive_data(exc.message),
                    "status_code": exc.status_code,
                    "request_id": req_id,
                    "context": exc.context,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = request_id_ctx.get()
        # Log the full exception internally with secrets masked
        logger.error(f"Unhandled server exception on {request.url.path}: {mask_sensitive_data(str(exc))}", exc_info=True)

        # Return safe response to client without leaking internal details or stack traces
        safe_msg = "An unexpected internal server error occurred. Please check logs with request_id."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": safe_msg,
                "error": {
                    "category": "INTERNAL_SERVER_ERROR",
                    "message": safe_msg,
                    "status_code": 500,
                    "request_id": req_id,
                },
            },
        )

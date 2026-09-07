"""
FactLens Observability Module.
"""

from backend.app.observability.errors import (
    CATEGORY_HTTP_STATUS,
    ErrorCategory,
    FactLensAPIException,
    register_error_handlers,
)
from backend.app.observability.logger import (
    configure_logging,
    get_logger,
    mask_sensitive_data,
    request_id_ctx,
)
from backend.app.observability.middleware import (
    ExecutionTimingMiddleware,
    RequestTracingMiddleware,
)
from backend.app.observability.retry import retry_with_backoff

__all__ = [
    "configure_logging",
    "get_logger",
    "mask_sensitive_data",
    "request_id_ctx",
    "RequestTracingMiddleware",
    "ExecutionTimingMiddleware",
    "ErrorCategory",
    "CATEGORY_HTTP_STATUS",
    "FactLensAPIException",
    "register_error_handlers",
    "retry_with_backoff",
]

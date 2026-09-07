"""
Observability middlewares for request tracing and execution latency measurement.
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.app.observability.logger import request_id_ctx


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Ensures every incoming HTTP request has a correlation UUID.
    Extracts existing 'X-Request-ID' header or generates a new one.
    Populates 'request_id_ctx' for structured log correlation and
    returns 'X-Request-ID' in the response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id or not req_id.strip():
            req_id = str(uuid.uuid4())

        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)


class ExecutionTimingMiddleware(BaseHTTPMiddleware):
    """
    Measures total request processing duration and adds 'X-Process-Time'
    header in milliseconds to the response.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"
        return response

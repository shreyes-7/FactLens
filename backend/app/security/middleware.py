"""
Security middlewares: In-memory sliding-window Rate Limiting and Security Headers.
"""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.app.config import Settings, get_settings
from backend.app.observability.logger import get_logger

logger = get_logger("factlens.security")


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding-window rate limiter per client IP address.
    Returns HTTP 429 Too Many Requests when the limit within a 60-second window is reached.
    """

    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()
        # Mapping from client IP -> list of timestamps
        self.request_history: dict[str, list[float]] = defaultdict(list)
        self.window_seconds = 60

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.settings.rate_limit_enabled:
            return await call_next(request)

        # Bypass rate limiting for documentation endpoints and favicon
        path = request.url.path
        if path in ("/docs", "/redoc", "/openapi.json", "/favicon.ico"):
            return await call_next(request)

        # Determine client IP (respecting X-Forwarded-For if behind a reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        now = time.time()
        window_start = now - self.window_seconds

        # Prune timestamps older than the sliding window
        timestamps = [ts for ts in self.request_history[client_ip] if ts > window_start]
        self.request_history[client_ip] = timestamps

        limit = self.settings.rate_limit_per_minute
        remaining = max(0, limit - len(timestamps))
        reset_seconds = int(self.window_seconds - (now - timestamps[0])) if timestamps else self.window_seconds

        if len(timestamps) >= limit:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {path} ({limit} req/min).")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "category": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit of {limit} requests per minute exceeded. Try again in {reset_seconds} seconds.",
                        "status_code": 429,
                    }
                },
                headers={
                    "Retry-After": str(reset_seconds),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_seconds),
                },
            )

        # Record this request
        timestamps.append(now)
        self.request_history[client_ip] = timestamps

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1 if remaining > 0 else 0)
        response.headers["X-RateLimit-Reset"] = str(reset_seconds)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects defensive HTTP response headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    """

    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        if self.settings.security_headers_enabled:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

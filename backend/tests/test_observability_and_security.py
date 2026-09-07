"""
Unit and integration tests for Phase 10: Observability, Security & Reliability.
"""

import re
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import app
from backend.app.observability.errors import (
    ErrorCategory,
    FactLensAPIException,
    register_error_handlers,
)
from backend.app.observability.logger import mask_sensitive_data
from backend.app.observability.middleware import (
    ExecutionTimingMiddleware,
    RequestTracingMiddleware,
)
from backend.app.observability.retry import retry_with_backoff
from backend.app.security.file_validation import sanitize_filename, validate_pdf_file
from backend.app.security.middleware import (
    RateLimitingMiddleware,
    SecurityHeadersMiddleware,
)


@pytest.fixture
def client():
    """Test client connected to the main FastAPI application."""
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. Observability: Request Tracing & Timing Headers
# -----------------------------------------------------------------------------

def test_request_id_generated_automatically(client):
    """When no X-Request-ID is sent, the server generates a UUID4 and returns it."""
    response = client.get("/")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    # Validate UUID pattern
    assert re.match(r"^[0-9a-f\-]{36}$", req_id)


def test_request_id_preserved_when_provided(client):
    """When an incoming X-Request-ID is supplied, the server preserves and echoes it."""
    custom_id = "test-tracing-correlation-id-12345"
    response = client.get("/", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_process_time_header_present(client):
    """Every response contains an X-Process-Time header with elapsed milliseconds."""
    response = client.get("/api/health")
    assert response.status_code == 200
    proc_time = response.headers.get("X-Process-Time")
    assert proc_time is not None
    assert re.match(r"^\d+(\.\d+)?ms$", proc_time)


# -----------------------------------------------------------------------------
# 2. Security: Response Headers
# -----------------------------------------------------------------------------

def test_security_headers_present(client):
    """Responses include standard defensive security headers."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers.get("Permissions-Policy", "")


# -----------------------------------------------------------------------------
# 3. Security: Rate Limiting
# -----------------------------------------------------------------------------

def test_rate_limiting_throttling():
    """Rate limiter allows requests under the limit and returns HTTP 429 when exceeded."""
    mini_app = FastAPI()
    test_settings = Settings(
        rate_limit_enabled=True,
        rate_limit_per_minute=3,
    )
    mini_app.add_middleware(RateLimitingMiddleware, settings=test_settings)

    @mini_app.get("/ping")
    def ping():
        return {"message": "pong"}

    mini_client = TestClient(mini_app)

    # First 3 requests succeed
    for i in range(3):
        res = mini_client.get("/ping")
        assert res.status_code == 200, f"Request {i+1} should succeed"
        assert "X-RateLimit-Remaining" in res.headers

    # 4th request exceeds rate limit
    res_exceeded = mini_client.get("/ping")
    assert res_exceeded.status_code == 429
    assert res_exceeded.headers.get("Retry-After") is not None
    assert res_exceeded.json()["error"]["category"] == "RATE_LIMIT_EXCEEDED"


# -----------------------------------------------------------------------------
# 4. Security: PDF File Validation & Sanitization
# -----------------------------------------------------------------------------

def test_validate_pdf_file_valid():
    """Valid PDF magic bytes (%PDF-) and size are accepted."""
    valid_pdf_content = b"%PDF-1.4 sample pdf content stream"
    sanitized = validate_pdf_file("annual_report.pdf", valid_pdf_content, max_file_size_mb=10)
    assert sanitized == "annual_report.pdf"


def test_validate_pdf_file_rejects_empty():
    """Empty files (0 bytes) are rejected with EMPTY_DOCUMENT category."""
    with pytest.raises(FactLensAPIException) as exc_info:
        validate_pdf_file("empty.pdf", b"")
    assert exc_info.value.category == ErrorCategory.EMPTY_DOCUMENT
    assert exc_info.value.status_code == 400


def test_validate_pdf_file_rejects_non_pdf_magic_bytes():
    """Disguised non-PDF files (e.g. plain text or exe) are rejected."""
    fake_pdf = b"Hello, this is just plain text, not a real PDF!"
    with pytest.raises(FactLensAPIException) as exc_info:
        validate_pdf_file("fake.pdf", fake_pdf)
    assert exc_info.value.category == ErrorCategory.INVALID_FILE
    assert "magic bytes" in exc_info.value.message.lower()


def test_validate_pdf_file_rejects_oversized():
    """Files exceeding max_file_size_mb are rejected with 413 Payload Too Large."""
    # 2 MB content with 1 MB limit
    large_pdf = b"%PDF-1.4 " + (b"0" * (2 * 1024 * 1024))
    with pytest.raises(FactLensAPIException) as exc_info:
        validate_pdf_file("large.pdf", large_pdf, max_file_size_mb=1)
    assert exc_info.value.status_code == 413
    assert exc_info.value.category == ErrorCategory.INVALID_FILE


def test_sanitize_filename():
    """Filename sanitization strips path traversal, slashes, and control characters."""
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\windows\\system32.pdf") == "system32.pdf"
    assert sanitize_filename("my report (final)!.pdf") == "my_report__final__.pdf"
    assert sanitize_filename("noextension") == "noextension.pdf"


# -----------------------------------------------------------------------------
# 5. Observability: Sensitive Data Masking
# -----------------------------------------------------------------------------

def test_mask_sensitive_data():
    """Credentials, tokens, and database passwords are automatically redacted."""
    # API key
    masked_key = mask_sensitive_data("Using api_key: gsk_1234567890abcdef12345 in call")
    assert "gsk_" not in masked_key
    assert "[REDACTED_KEY]" in masked_key

    # Bearer token
    masked_token = mask_sensitive_data("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    assert "eyJhbGci" not in masked_token
    assert "[REDACTED_TOKEN]" in masked_token

    # PostgreSQL password
    masked_db = mask_sensitive_data("Connected to postgresql://postgres:MySecretPass123@db.supabase.co:5432/postgres")
    assert "MySecretPass123" not in masked_db
    assert "[REDACTED_PASSWORD]" in masked_db


# -----------------------------------------------------------------------------
# 6. Observability: Error Classification & Structured Exceptions
# -----------------------------------------------------------------------------

def test_structured_error_handling():
    """Custom FactLensAPIException returns standardized RFC-compliant error format."""
    mini_app = FastAPI()
    register_error_handlers(mini_app)

    @mini_app.get("/trigger-error")
    def trigger_error():
        raise FactLensAPIException(
            message="LLM extraction timed out after 3 attempts.",
            category=ErrorCategory.LLM_ERROR,
            context={"model": "gemini-1.5-pro", "timeout_sec": 30},
        )

    mini_client = TestClient(mini_app)
    response = mini_client.get("/trigger-error")
    assert response.status_code == 502
    data = response.json()
    assert "error" in data
    assert data["error"]["category"] == "LLM_ERROR"
    assert data["error"]["status_code"] == 502
    assert "timed out" in data["error"]["message"]
    assert data["error"]["context"]["model"] == "gemini-1.5-pro"


# -----------------------------------------------------------------------------
# 7. Reliability: Retry with Exponential Backoff
# -----------------------------------------------------------------------------

def test_retry_sync_success_after_failure():
    """Sync function retries on transient errors and succeeds when condition clears."""
    attempts = 0

    @retry_with_backoff(max_attempts=3, initial_delay=0.01, jitter=False, retry_on=(ConnectionError,))
    def flaky_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Temporary network reset")
        return "SUCCESS"

    result = flaky_operation()
    assert result == "SUCCESS"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_async_fails_fast_on_non_retriable_error():
    """Async function fails fast on excluded errors without retrying."""
    attempts = 0

    @retry_with_backoff(max_attempts=3, initial_delay=0.01, exclude=(ValueError,))
    async def invalid_call():
        nonlocal attempts
        attempts += 1
        raise ValueError("Invalid parameters cannot be retried")

    with pytest.raises(ValueError):
        await invalid_call()

    # Must have failed on the first attempt without retrying
    assert attempts == 1
